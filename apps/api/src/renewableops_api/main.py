"""Observable, input-validated API for forecasts, scenarios and public snapshots."""

from __future__ import annotations

import io
import json
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Lock
from typing import Any, cast

import joblib
import numpy as np
import pandas as pd
import structlog
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from renewableops.assets import asset_lookup
from renewableops.battery import optimize_dispatch
from renewableops.config import MODEL_DIR, PUBLIC_DATA_DIR, Settings
from renewableops.features import FEATURE_COLUMNS
from renewableops.vision import inspect_image

from .schemas import (
    BatteryDispatchRequest,
    BatteryDispatchResponse,
    ForecastRequest,
    ForecastResponse,
    ScenarioRequest,
    ScenarioResponse,
)

settings = Settings()
logger = structlog.get_logger()
REQUEST_COUNT = Counter(
    "renewableops_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "renewableops_http_request_duration_seconds", "HTTP latency", ["method", "path"]
)
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60.0
RATE_WINDOWS: defaultdict[str, deque[float]] = defaultdict(deque)
RATE_LOCK = Lock()

app = FastAPI(
    title="RenewableOps AI API",
    version="1.0.0",
    description=(
        "Decision-support API for a reproducible renewable operations portfolio demo. "
        "It never controls physical equipment."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Correlation-ID", "X-Webhook-Signature"],
)


def _rate_limited(client_key: str, now: float) -> bool:
    with RATE_LOCK:
        window = RATE_WINDOWS[client_key]
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= RATE_LIMIT_REQUESTS:
            return True
        window.append(now)
        return False


@app.middleware("http")
async def observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    status = 500
    try:
        client_key = request.client.host if request.client else "unknown"
        exempt = request.url.path.startswith(("/health/", "/metrics"))
        response: Response
        if not exempt and _rate_limited(client_key, started):
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "RATE_LIMITED",
                        "message": "Local demo limit exceeded; retry in one minute.",
                    }
                },
                headers={"Retry-After": "60"},
            )
        else:
            response = await call_next(request)
        status = response.status_code
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    finally:
        elapsed = time.perf_counter() - started
        REQUEST_COUNT.labels(request.method, request.url.path, str(status)).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=status,
            elapsed_ms=round(elapsed * 1000, 2),
            correlation_id=correlation_id,
        )


def _dashboard() -> dict[str, Any]:
    path = PUBLIC_DATA_DIR / "latest" / "dashboard.json"
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail={"code": "SNAPSHOT_NOT_READY", "message": "Run `renewableops run-demo` first."},
        )
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail="Public snapshot is malformed")
    return cast(dict[str, Any], payload)


def _dashboard_rows(key: str) -> list[dict[str, object]]:
    value: object = _dashboard().get(key)
    if not isinstance(value, list):
        raise HTTPException(status_code=503, detail=f"Snapshot field {key!r} is malformed")
    return [
        {str(field): field_value for field, field_value in row.items()}
        for row in value
        if isinstance(row, dict)
    ]


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "healthy", "service": "renewableops-api"}


@app.get("/health/ready", tags=["health"])
def ready() -> dict[str, object]:
    snapshot_ready = (PUBLIC_DATA_DIR / "latest" / "dashboard.json").exists()
    models_ready = all(
        (MODEL_DIR / name).exists()
        for name in (
            "solar_forecast_champion.joblib",
            "wind_forecast_champion.joblib",
            "cv_solar_champion.joblib",
        )
    )
    if not snapshot_ready:
        raise HTTPException(status_code=503, detail="Public snapshot is not ready")
    return {"status": "ready", "snapshot": snapshot_ready, "models": models_ready}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/overview", tags=["portfolio"])
def overview() -> dict[str, object]:
    payload = _dashboard()
    return {
        "meta": payload["meta"],
        "kpis": payload["kpis"],
        "series": payload["series"],
        "mix": payload["mix"],
    }


@app.get("/api/v1/assets", tags=["portfolio"])
def assets(technology: str | None = None, region: str | None = None) -> list[dict[str, object]]:
    rows = _dashboard_rows("assets")
    if technology:
        rows = [row for row in rows if row["technology"] == technology]
    if region:
        rows = [row for row in rows if row["region"] == region]
    return rows


@app.get("/api/v1/anomalies", tags=["operations"])
def anomalies() -> list[dict[str, object]]:
    return _dashboard_rows("anomalies")


@app.get("/api/v1/models", tags=["mlops"])
def models() -> dict[str, object]:
    payload = _dashboard()
    return {"champions": payload["champions"], "metrics": payload["model_metrics"]}


@app.post("/api/v1/forecast", response_model=ForecastResponse, tags=["forecast"])
def forecast(request: ForecastRequest) -> ForecastResponse:
    artifact_path = MODEL_DIR / f"{request.technology}_forecast_champion.joblib"
    if not artifact_path.exists():
        raise HTTPException(status_code=503, detail="Forecast model is not ready")
    artifact = joblib.load(artifact_path)
    values = request.model_dump()
    installed_capacity = float(values.pop("installed_capacity_mw"))
    values.pop("technology")
    features = pd.DataFrame([{column: values[column] for column in FEATURE_COLUMNS}])
    p50 = float(np.clip(artifact["model"].predict(features)[0], 0, installed_capacity))
    low, high = artifact["residual_quantiles"]
    return ForecastResponse(
        technology=request.technology,
        model=artifact["model_name"],
        p10_mw=round(max(0, p50 + low), 4),
        p50_mw=round(p50, 4),
        p90_mw=round(min(installed_capacity, p50 + high), 4),
    )


@app.post("/api/v1/scenarios", response_model=ScenarioResponse, tags=["operations"])
def run_scenario(request: ScenarioRequest) -> ScenarioResponse:
    assets_by_id = asset_lookup()
    if request.asset_id not in assets_by_id:
        raise HTTPException(status_code=404, detail="Unknown asset_id")
    asset = assets_by_id[request.asset_id]
    technology_compatibility = {
        "soiling": "solar",
        "inverter_loss": "solar",
        "wind_vibration": "wind",
    }
    required = technology_compatibility.get(request.scenario)
    if required and asset["technology"] != required:
        raise HTTPException(
            status_code=422,
            detail=f"Scenario {request.scenario} requires a {required} asset",
        )
    detection = {
        "soiling": ("Residual + Isolation Forest", "Schedule thermographic inspection"),
        "inverter_loss": ("Physical production rule", "Verify inverter alarms"),
        "wind_vibration": ("Robust vibration score", "Plan safe maintenance window"),
        "source_outage": ("Freshness SLA", "Serve last-valid snapshot"),
        "model_drift": ("nMAE + PSI monitor", "Train challenger; require approval"),
    }
    detected_by, action = detection[request.scenario]
    scenario_key = f"{request.scenario}:{request.asset_id}:{request.seed}"
    run_uuid = uuid.uuid5(uuid.NAMESPACE_URL, scenario_key)
    run_id = f"scn-{run_uuid}"
    affected = asset["capacity_mw"] * request.duration_hours * request.severity / 100 * 0.18
    return ScenarioResponse(
        run_id=run_id,
        status="completed",
        detected_by=detected_by,
        detection_seconds=max(9, 74 - request.severity // 2),
        estimated_mwh_at_risk=round(affected, 2),
        action=action,
        audit_event_id=f"AUD-{run_uuid.hex[:10].upper()}",
    )


@app.post(
    "/api/v1/battery/dispatch",
    response_model=BatteryDispatchResponse,
    tags=["market"],
)
def battery_dispatch(request: BatteryDispatchRequest) -> BatteryDispatchResponse:
    try:
        schedule, margin = optimize_dispatch(**request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return BatteryDispatchResponse(
        schedule=[
            {
                "horizon_hour": item.horizon_hour,
                "price_eur_mwh": item.price_eur_mwh,
                "charge_mw": item.charge_mw,
                "discharge_mw": item.discharge_mw,
                "state_of_charge_mwh": item.state_of_charge_mwh,
                "cashflow_eur": item.cashflow_eur,
            }
            for item in schedule
        ],
        estimated_margin_eur=margin,
    )


@app.post("/api/v1/inspections", tags=["computer-vision"])
async def inspect(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP are supported")
    body = await file.read(settings.max_upload_bytes + 1)
    if len(body) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB limit")
    try:
        verified_image = Image.open(io.BytesIO(body))
        verified_image.verify()
        decoded_image = Image.open(io.BytesIO(body)).convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=422, detail="Invalid or corrupted image") from error
    width, height = decoded_image.size
    if width * height > 24_000_000:
        raise HTTPException(status_code=413, detail="Decoded image dimensions are too large")
    result = inspect_image(np.asarray(decoded_image))
    return {
        "inspection_id": f"VIS-{uuid.uuid4()}",
        "filename": Path(file.filename or "upload").name,
        **result,
    }
