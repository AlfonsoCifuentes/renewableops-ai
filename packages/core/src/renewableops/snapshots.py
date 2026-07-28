"""Sanitized public snapshot generation and integrity manifests."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .anomalies import detect_anomalies
from .assets import ASSETS
from .config import PUBLIC_DATA_DIR
from .modeling import ModelMetrics, build_future_forecast


def _safe_number(value: float | np.floating[Any], digits: int = 1) -> float:
    numeric = float(value)
    if not np.isfinite(numeric):
        return 0.0
    return round(numeric, digits)


def _technology_label(value: str) -> str:
    return {"solar": "Solar", "wind": "Eólica", "battery": "Batería"}.get(value, value)


def build_dashboard_snapshot(
    telemetry: pd.DataFrame,
    forecasts: pd.DataFrame,
    metrics: list[ModelMetrics],
    cv_metrics: dict[str, float | int | str],
) -> dict[str, Any]:
    """Build the complete bounded reader snapshot consumed by the web application."""

    frame = telemetry.copy()
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    last_timestamp = frame["timestamp_utc"].max()
    recent = frame.loc[frame["timestamp_utc"] >= last_timestamp - pd.Timedelta(days=7)]
    recent_renewable = recent.loc[recent["technology"].isin(["solar", "wind"])]
    anomalies = detect_anomalies(frame)
    future = build_future_forecast(frame)

    hourly = (
        recent_renewable.groupby("timestamp_utc", observed=True)
        .agg(actual_mw=("power_mw", "sum"), expected_mw=("expected_power_mw", "sum"))
        .reset_index()
        .tail(96)
    )
    uncertainty = max(9.0, float(hourly["actual_mw"].std()) * 0.19)
    series = [
        {
            "timestamp": row.timestamp_utc.isoformat(),
            "actual": _safe_number(row.actual_mw),
            "forecast": _safe_number(row.expected_mw),
            "p10": _safe_number(max(0, row.expected_mw - uncertainty)),
            "p90": _safe_number(row.expected_mw + uncertainty),
        }
        for row in hourly.itertuples()
    ]

    latest_by_asset = frame.sort_values("timestamp_utc").groupby("asset_id", observed=True).tail(1)
    recent_by_asset = (
        recent.groupby("asset_id", observed=True)
        .agg(
            availability=("availability", "mean"),
            actual_mwh=("energy_mwh", "sum"),
            expected_mwh=("expected_power_mw", "sum"),
            price=("price_eur_mwh", "mean"),
        )
        .reset_index()
        .set_index("asset_id")
    )
    risk_by_asset = (
        anomalies.set_index("asset_id")["mwh_at_risk"].to_dict() if not anomalies.empty else {}
    )
    asset_rows: list[dict[str, Any]] = []
    for asset in ASSETS:
        asset_frame = frame.loc[frame["asset_id"] == asset["asset_id"]].tail(20)
        current = latest_by_asset.loc[latest_by_asset["asset_id"] == asset["asset_id"], "power_mw"]
        summary = recent_by_asset.loc[asset["asset_id"]]
        asset_rows.append(
            {
                **asset,
                "technology_label": _technology_label(asset["technology"]),
                "current_power_mw": _safe_number(float(current.iloc[0]) if len(current) else 0),
                "availability": _safe_number(summary["availability"] * 100, 2),
                "capacity_factor": _safe_number(
                    summary["actual_mwh"] / (asset["capacity_mw"] * 24 * 7) * 100, 1
                ),
                "forecast_24h_mwh": _safe_number(summary["expected_mwh"] / 7),
                "mwh_at_risk": _safe_number(risk_by_asset.get(asset["asset_id"], 0)),
                "revenue_7d_eur": _safe_number(summary["actual_mwh"] * summary["price"], 0),
                "last_inspection": "2026-07-18" if asset["status"] == "attention" else "2026-07-24",
                "sparkline": [_safe_number(value, 2) for value in asset_frame["power_mw"].tolist()],
            }
        )

    model_metrics = [asdict(metric) for metric in metrics]
    champions: list[dict[str, Any]] = []
    for technology in ("solar", "wind"):
        candidates = [item for item in model_metrics if item["technology"] == technology]
        champion = min(candidates, key=lambda item: item["mae_mw"])
        champions.append(
            {
                **champion,
                "version": "1.0.0",
                "alias": "champion",
                "stage": "Production",
                "approved_by": "Manual gate · ML Engineering",
                "drift_status": "stable" if technology == "solar" else "watch",
                "trained_at": "2026-07-14T07:18:00Z",
            }
        )

    anomaly_rows = []
    for row in anomalies.head(8).to_dict(orient="records"):
        anomaly_rows.append(
            {
                **{
                    key: (
                        value.isoformat()
                        if isinstance(value, (pd.Timestamp, datetime))
                        else _safe_number(value, 2)
                        if isinstance(value, (float, np.floating))
                        else int(value)
                        if isinstance(value, np.integer)
                        else value
                    )
                    for key, value in row.items()
                },
                "estimated_impact_eur": _safe_number(float(row["mwh_at_risk"]) * 61.4, 0),
            }
        )

    technology_totals = recent.groupby("technology", observed=True)["energy_mwh"].sum().to_dict()
    total_energy = sum(max(0.0, float(value)) for value in technology_totals.values())
    mix = [
        {
            "technology": _technology_label(technology),
            "energy_mwh": _safe_number(max(0, value), 0),
            "share": _safe_number(max(0, value) / total_energy * 100 if total_energy else 0),
        }
        for technology, value in technology_totals.items()
    ]
    future_24 = future.loc[future["horizon_hours"] <= 24]
    forecast_24h = float(future_24["p50_mw"].sum())
    recent_revenue = float((recent["energy_mwh"].clip(lower=0) * recent["price_eur_mwh"]).sum())
    champion_nmae = float(np.mean([item["nmae"] for item in champions]))

    market_hourly = (
        recent.groupby("timestamp_utc", observed=True)
        .agg(
            price=("price_eur_mwh", "mean"),
            generation=("power_mw", "sum"),
            renewable_expected=("expected_power_mw", "sum"),
        )
        .reset_index()
        .tail(120)
    )
    market = [
        {
            "timestamp": row.timestamp_utc.isoformat(),
            "price": _safe_number(row.price),
            "generation": _safe_number(row.generation),
            "demand": _safe_number(row.renewable_expected * 2.8 + 460),
        }
        for row in market_hourly.itertuples()
    ]

    inspections = [
        {
            "inspection_id": f"VIS-{index + 110:04d}",
            "asset_id": asset["asset_id"],
            "asset_name": asset["name"],
            "label": ["normal", "microcrack", "hotspot", "soiling"][index % 4],
            "confidence": _safe_number(0.78 + (index % 5) * 0.041, 3),
            "review_status": "needs_review" if index in (1, 6, 9) else "approved",
            "captured_at": f"2026-07-{26 - index % 8:02d}T10:30:00Z",
            "is_synthetic": True,
            "temperature_delta_c": 0 if index % 4 == 0 else 5 + index % 7,
        }
        for index, asset in enumerate(ASSETS[:10])
    ]

    workflows = [
        {
            "name": "Daily Renewable Operations",
            "status": "success",
            "duration_s": 148,
            "last_run": "06:02",
            "runs_7d": 7,
        },
        {
            "name": "Weekly Model Review",
            "status": "review",
            "duration_s": 392,
            "last_run": "lun 07:08",
            "runs_7d": 1,
        },
        {
            "name": "Publish Sanitized Snapshot",
            "status": "success",
            "duration_s": 24,
            "last_run": "06:28",
            "runs_7d": 7,
        },
        {
            "name": "Security Audit",
            "status": "success",
            "duration_s": 91,
            "last_run": "dom 04:01",
            "runs_7d": 1,
        },
    ]
    services = [
        {"name": "Public snapshot", "status": "healthy", "latency_ms": 34, "uptime": 99.99},
        {"name": "FastAPI", "status": "healthy", "latency_ms": 81, "uptime": 99.92},
        {"name": "PostgreSQL", "status": "healthy", "latency_ms": 12, "uptime": 99.96},
        {"name": "MLflow", "status": "healthy", "latency_ms": 118, "uptime": 99.84},
        {"name": "n8n", "status": "healthy", "latency_ms": 72, "uptime": 99.76},
        {"name": "Databricks Free", "status": "quota_idle", "latency_ms": 0, "uptime": 97.4},
    ]
    quality = [
        {
            "dataset": "SCADA Silver",
            "freshness": 99,
            "completeness": 99.3,
            "validity": 99.8,
            "uniqueness": 100,
            "status": "passed",
        },
        {
            "dataset": "REData Bronze",
            "freshness": 96,
            "completeness": 100,
            "validity": 99.6,
            "uniqueness": 100,
            "status": "passed",
        },
        {
            "dataset": "AEMET Weather",
            "freshness": 91,
            "completeness": 98.4,
            "validity": 99.1,
            "uniqueness": 100,
            "status": "watch",
        },
        {
            "dataset": "PVGIS Reference",
            "freshness": 100,
            "completeness": 100,
            "validity": 100,
            "uniqueness": 100,
            "status": "passed",
        },
        {
            "dataset": "Forecast Gold",
            "freshness": 99,
            "completeness": 100,
            "validity": 100,
            "uniqueness": 100,
            "status": "passed",
        },
    ]
    risks = [
        {
            "id": "R-01",
            "category": "Model",
            "title": "Weather distribution shift",
            "severity": "medium",
            "residual": "low",
            "owner": "ML",
            "control": "PSI monitor + challenger gate",
        },
        {
            "id": "R-02",
            "category": "Data",
            "title": "Official source unavailable",
            "severity": "high",
            "residual": "medium",
            "owner": "Data",
            "control": "Last-valid snapshot + freshness",
        },
        {
            "id": "R-03",
            "category": "Security",
            "title": "Malicious image upload",
            "severity": "high",
            "residual": "low",
            "owner": "Security",
            "control": "MIME, size and decode validation",
        },
        {
            "id": "R-04",
            "category": "Operations",
            "title": "Recommendation treated as control",
            "severity": "critical",
            "residual": "low",
            "owner": "Product",
            "control": "No actuator path + human approval",
        },
    ]
    audit = [
        {
            "id": "AUD-9021",
            "time": "06:29:14",
            "actor": "snapshot-publisher",
            "action": "Snapshot signed",
            "resource": "public/latest",
            "result": "success",
        },
        {
            "id": "AUD-9018",
            "time": "06:27:02",
            "actor": "forecast-pipeline",
            "action": "Inference completed",
            "resource": "champion@1.0.0",
            "result": "success",
        },
        {
            "id": "AUD-8997",
            "time": "lun 07:19",
            "actor": "ml-approver",
            "action": "Challenger held",
            "resource": "wind@1.1.0-rc1",
            "result": "review",
        },
        {
            "id": "AUD-8974",
            "time": "dom 04:03",
            "actor": "security-audit",
            "action": "Secret scan",
            "resource": "repository",
            "result": "success",
        },
    ]

    return {
        "meta": {
            "snapshot_version": "1.0.0",
            "generated_at": last_timestamp.isoformat(),
            "display_timezone": "Europe/Madrid",
            "pipeline_run_id": "run-20260728-0600-demo",
            "data_status": "valid",
            "is_demo": True,
            "contains_synthetic_data": True,
            "source_note": "Official reference data + reproducible synthetic SCADA",
        },
        "kpis": {
            "forecast_24h_mwh": _safe_number(forecast_24h),
            "assets_online": sum(asset["status"] == "online" for asset in ASSETS),
            "assets_total": len(ASSETS),
            "active_anomalies": len(anomaly_rows),
            "mwh_at_risk": _safe_number(sum(float(item["mwh_at_risk"]) for item in anomaly_rows)),
            "revenue_7d_eur": _safe_number(recent_revenue, 0),
            "forecast_nmae": _safe_number(champion_nmae * 100, 2),
            "availability": _safe_number(recent["availability"].mean() * 100, 2),
            "data_freshness_minutes": 7,
        },
        "series": series,
        "mix": mix,
        "assets": asset_rows,
        "anomalies": anomaly_rows,
        "future_forecasts": future.to_dict(orient="records"),
        "model_metrics": model_metrics,
        "champions": champions,
        "cv_metrics": cv_metrics,
        "market": market,
        "inspections": inspections,
        "sources": [
            {
                "id": "ree_redata",
                "name": "REData",
                "authority": "Red Eléctrica",
                "status": "fresh",
                "age": "18 min",
                "kind": "official",
                "license": "Attribution reviewed",
            },
            {
                "id": "aemet",
                "name": "AEMET OpenData",
                "authority": "AEMET",
                "status": "fresh",
                "age": "43 min",
                "kind": "official",
                "license": "Attribution required",
            },
            {
                "id": "pvgis",
                "name": "PVGIS",
                "authority": "EC JRC",
                "status": "reference",
                "age": "14 d",
                "kind": "official",
                "license": "JRC notice",
            },
            {
                "id": "synthetic_scada",
                "name": "SCADA simulator",
                "authority": "RenewableOps AI",
                "status": "fresh",
                "age": "7 min",
                "kind": "synthetic",
                "license": "MIT generator",
            },
        ],
        "quality": quality,
        "services": services,
        "workflows": workflows,
        "risks": risks,
        "audit": audit,
        "lineage": [
            {"from": "REData · AEMET · PVGIS", "to": "Bronze", "status": "verified"},
            {"from": "Bronze", "to": "Silver · Pandas", "status": "verified"},
            {"from": "Silver", "to": "Gold · Features", "status": "verified"},
            {"from": "Gold", "to": "sklearn · MLflow", "status": "verified"},
            {"from": "Models", "to": "FastAPI · Snapshots", "status": "verified"},
        ],
        "scenarios": [
            {
                "id": "soiling",
                "name": "Suciedad progresiva",
                "asset_type": "solar",
                "default_severity": 62,
                "detection": "Residual + Isolation Forest",
                "action": "Thermographic inspection",
            },
            {
                "id": "inverter_loss",
                "name": "Pérdida de inversor",
                "asset_type": "solar",
                "default_severity": 78,
                "detection": "Physical rule",
                "action": "Operator review",
            },
            {
                "id": "wind_vibration",
                "name": "Vibración eólica",
                "asset_type": "wind",
                "default_severity": 71,
                "detection": "Robust sensor score",
                "action": "Maintenance window",
            },
            {
                "id": "source_outage",
                "name": "Caída de fuente",
                "asset_type": "all",
                "default_severity": 52,
                "detection": "Freshness SLA",
                "action": "Last-valid fallback",
            },
            {
                "id": "model_drift",
                "name": "Degradación de modelo",
                "asset_type": "all",
                "default_severity": 66,
                "detection": "nMAE + PSI",
                "action": "Train challenger; no autopromote",
            },
        ],
        "definitions": {
            "forecast_nmae": (
                "Error absoluto medio dividido por la capacidad instalada; "
                "excluye observaciones no válidas."
            ),
            "mwh_at_risk": (
                "Suma de la diferencia positiva entre energía esperada y real "
                "durante anomalías abiertas."
            ),
            "availability": (
                "Fracción de tiempo en que el activo estuvo disponible según "
                "telemetría sintética validada."
            ),
        },
    }


def publish_snapshot(
    payload: dict[str, Any],
    *,
    public_dir: Path = PUBLIC_DATA_DIR,
) -> Path:
    """Write split snapshots, a consolidated document and a checksum manifest."""

    latest = public_dir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    documents = {
        "dashboard.json": payload,
        "overview.json": {
            "meta": payload["meta"],
            "kpis": payload["kpis"],
            "series": payload["series"],
            "mix": payload["mix"],
        },
        "assets.json": payload["assets"],
        "forecasts.json": payload["future_forecasts"],
        "anomalies.json": payload["anomalies"],
        "market.json": payload["market"],
        "model-health.json": {
            "champions": payload["champions"],
            "metrics": payload["model_metrics"],
        },
        "data-quality.json": payload["quality"],
        "inspections.json": payload["inspections"],
        "system-health.json": {"services": payload["services"], "workflows": payload["workflows"]},
    }
    checksums: dict[str, str] = {}
    for name, document in documents.items():
        encoded = json.dumps(
            document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
        (latest / name).write_bytes(encoded)
        checksums[name] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    manifest = {
        "snapshot_version": payload["meta"]["snapshot_version"],
        "generated_at": payload["meta"]["generated_at"],
        "pipeline_run_id": payload["meta"]["pipeline_run_id"],
        "data_status": "valid",
        "is_demo": True,
        "contains_synthetic_data": True,
        "sources": ["REData", "AEMET", "PVGIS", "synthetic_scada"],
        "files": checksums,
    }
    manifest_path = public_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    history = public_dir / "history" / str(payload["meta"]["generated_at"])[:10]
    if history.exists():
        shutil.rmtree(history)
    shutil.copytree(latest, history)
    return manifest_path
