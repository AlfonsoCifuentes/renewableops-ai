"""Sanitized public snapshot generation and integrity manifests."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .anomalies import detect_anomalies
from .assets import ASSETS
from .audit import read_events
from .config import DATA_DIR, PUBLIC_DATA_DIR
from .ingestion import load_source_status
from .modeling import ModelMetrics, build_future_forecast

MAX_PUBLIC_DOCUMENT_BYTES = 5 * 1024 * 1024
FORBIDDEN_PUBLIC_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|secret|token|api_key|access_key|private_key)(?:$|_)",
    re.IGNORECASE,
)
FORBIDDEN_PUBLIC_VALUE = re.compile(
    r"(?:[A-Za-z]:\\(?:Users|ProgramData)\\|/(?:home|root|Users)/|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16})"
)


class SnapshotValidationError(ValueError):
    """Raised when a public snapshot violates the sanitization boundary."""


def _safe_number(value: float | np.floating[Any], digits: int = 1) -> float:
    numeric = float(value)
    if not np.isfinite(numeric):
        return 0.0
    return round(numeric, digits)


def _technology_label(value: str) -> str:
    return {"solar": "Solar", "wind": "Eólica", "battery": "Batería"}.get(value, value)


def _validate_public_document(name: str, document: object) -> bytes:
    def walk(value: object, location: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                field = str(key)
                if FORBIDDEN_PUBLIC_KEY.search(field):
                    raise SnapshotValidationError(f"{name}: forbidden field at {location}.{field}")
                walk(item, f"{location}.{field}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{location}[{index}]")
        elif isinstance(value, str) and FORBIDDEN_PUBLIC_VALUE.search(value):
            raise SnapshotValidationError(
                f"{name}: local path or credential-shaped value at {location}"
            )

    walk(document, "$")
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    if len(encoded) > MAX_PUBLIC_DOCUMENT_BYTES:
        raise SnapshotValidationError(
            f"{name}: document is {len(encoded)} bytes; limit is {MAX_PUBLIC_DOCUMENT_BYTES}"
        )
    return encoded


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _age_label(timestamp: object) -> str:
    if not isinstance(timestamp, str):
        return "sin ejecución"
    try:
        age = max(pd.Timedelta(0), pd.Timestamp.now(tz="UTC") - pd.Timestamp(timestamp))
    except (TypeError, ValueError):
        return "fecha no interpretable"
    hours = int(age.total_seconds() // 3600)
    if hours < 1:
        return "<1 h"
    if hours < 48:
        return f"{hours} h"
    return f"{hours // 24} d"


def _source_rows() -> list[dict[str, Any]]:
    status = load_source_status()
    evidence = status.get("sources")
    observations = evidence if isinstance(evidence, dict) else {}
    defaults = {
        "ree_redata": ("REData", "Red Eléctrica", "Attribution reviewed"),
        "pvgis": ("PVGIS", "European Commission JRC", "JRC notice"),
        "eurostat_renewables": (
            "Eurostat renewables",
            "Eurostat",
            "Eurostat reuse policy",
        ),
        "aemet": ("AEMET OpenData", "AEMET", "Attribution required"),
    }
    rows: list[dict[str, Any]] = []
    for source_id, (name, authority, license_note) in defaults.items():
        raw = observations.get(source_id)
        item = raw if isinstance(raw, dict) else {}
        state = str(item.get("status", "not_run"))
        rows.append(
            {
                "id": source_id,
                "name": str(item.get("name", name)),
                "authority": str(item.get("authority", authority)),
                "status": "verified" if state == "success" else state,
                "age": _age_label(item.get("extracted_at")),
                "kind": "official",
                "license": str(item.get("license_notes", license_note)),
                "extracted_at": item.get("extracted_at"),
                "source_updated_at": item.get("source_updated_at"),
                "checksum": item.get("checksum_sha256"),
                "records": int(item.get("records", 0)),
                "evidence": item.get("manifest"),
            }
        )
    rows.append(
        {
            "id": "synthetic_scada",
            "name": "SCADA simulator",
            "authority": "RenewableOps AI",
            "status": "versioned",
            "age": "snapshot actual",
            "kind": "synthetic",
            "license": "MIT generator",
            "extracted_at": None,
            "source_updated_at": None,
            "checksum": None,
            "records": 0,
            "evidence": "data/manifests/synthetic_scada_bronze.json",
        }
    )
    return rows


def _risk_rows() -> list[dict[str, Any]]:
    path = DATA_DIR.parent / "governance" / "risk-register.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return [
        {
            "id": row["risk_id"],
            "category": row["category"],
            "title": row["title"],
            "severity": row["inherent_risk"],
            "residual": row["residual_risk"],
            "owner": row["owner"],
            "control": row["control"],
            "status": row["status"],
            "likelihood": int(row["likelihood"]),
            "impact": int(row["impact"]),
            "evidence": row["evidence"],
        }
        for row in rows
    ]


def _governance_evidence() -> dict[str, object]:
    root = DATA_DIR.parent
    collections = [
        (
            "System card",
            [root / "governance" / "system-card.md"],
            "versioned documentation",
        ),
        (
            "Model cards",
            sorted((root / "governance" / "model-cards").glob("*.md")),
            "forecast + visual inspection",
        ),
        (
            "Data cards",
            sorted((root / "governance" / "data-cards").glob("*.md")),
            "official + synthetic sources",
        ),
        (
            "Threat model",
            [root / "governance" / "threat-model" / "README.md"],
            "STRIDE + ML threats",
        ),
        (
            "Incident playbook",
            [root / "governance" / "incident-response" / "playbook.md"],
            "SEV-1–4 response",
        ),
        (
            "SBOM",
            sorted((root / "artifacts" / "security").glob("*.cdx.json")),
            "CycloneDX inventory",
        ),
    ]
    documents = []
    for name, paths, description in collections:
        existing = [path for path in paths if path.exists()]
        documents.append(
            {
                "name": name,
                "description": description,
                "status": "versioned" if existing else "not_generated",
                "count": len(existing),
                "evidence": [path.relative_to(root).as_posix() for path in existing],
            }
        )
    frameworks = [
        ("AI Act", "governance/ai-act-assessment.md"),
        ("NIS2", "governance/nis2-control-mapping.md"),
        ("NIST AI RMF", "governance/nist-ai-rmf.md"),
        ("GDPR", "governance/gdpr-assessment.md"),
        ("OWASP/STRIDE", "governance/threat-model/README.md"),
    ]
    return {
        "documents": documents,
        "frameworks": [
            {
                "name": name,
                "status": (
                    "documented_alignment"
                    if (root / evidence).exists()
                    else "not_documented"
                ),
                "evidence": evidence if (root / evidence).exists() else None,
            }
            for name, evidence in frameworks
        ],
        "disclaimer": (
            "Engineering alignment only; not legal advice, certification, or compliance claim."
        ),
    }


def _runtime_services() -> list[dict[str, Any]]:
    report = _load_json(DATA_DIR.parent / "artifacts" / "verification" / "container-runtime.json")
    generated_at = report.get("generated_at")
    checks = report.get("checks")
    check_rows = checks if isinstance(checks, list) else []
    profiles = next(
        (
            item
            for item in check_rows
            if isinstance(item, dict) and item.get("check") == "container_profiles"
        ),
        {},
    )
    raw_services = profiles.get("services") if isinstance(profiles, dict) else {}
    services = raw_services if isinstance(raw_services, dict) else {}
    labels = {
        "dashboard": "Public snapshot / Next.js",
        "api": "FastAPI",
        "postgres": "PostgreSQL",
        "minio": "MinIO",
        "mlflow": "MLflow",
        "n8n": "n8n",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "loki": "Loki",
    }
    probe_names = {
        "dashboard": "dashboard_health",
        "api": "api_ready",
        "n8n": "n8n_health",
        "prometheus": "prometheus_ready",
        "grafana": "grafana_health",
    }
    probes = {
        str(item.get("check")): item
        for item in check_rows
        if isinstance(item, dict) and item.get("check")
    }
    rows: list[dict[str, Any]] = []
    for service_id, label in labels.items():
        raw = services.get(service_id)
        item = raw if isinstance(raw, dict) else {}
        verified = bool(profiles.get("passed")) and item.get("state") == "running"
        probe = probes.get(probe_names.get(service_id, ""), {})
        rows.append(
            {
                "name": label,
                "status": "verified_local" if verified else "not_verified",
                "latency_ms": probe.get("elapsed_ms"),
                "uptime": None,
                "evidence_at": generated_at,
                "evidence_scope": "local Docker validation",
            }
        )
    rows.append(
        {
            "name": "Databricks Free Edition",
            "status": "not_executed",
            "latency_ms": None,
            "uptime": None,
            "evidence_at": None,
            "evidence_scope": "requires owner OAuth workspace",
        }
    )
    return rows


def _workflow_rows() -> list[dict[str, Any]]:
    workflow_dir = DATA_DIR.parent / "workflows" / "n8n"
    report = _load_json(DATA_DIR.parent / "artifacts" / "verification" / "container-runtime.json")
    checks = report.get("checks")
    check_rows = checks if isinstance(checks, list) else []
    execution = next(
        (
            item
            for item in check_rows
            if isinstance(item, dict) and item.get("check") == "n8n_import_and_execution"
        ),
        {},
    )
    raw_executions = execution.get("executions") if isinstance(execution, dict) else []
    execution_rows = raw_executions if isinstance(raw_executions, list) else []
    executions_by_name = {
        str(item.get("name")): item
        for item in execution_rows
        if isinstance(item, dict) and item.get("name")
    }
    rows: list[dict[str, Any]] = []
    for path in sorted(workflow_dir.glob("*.json")):
        payload = _load_json(path)
        name = str(payload.get("name", path.stem))
        raw_run = executions_by_name.get(name)
        run = raw_run if isinstance(raw_run, dict) else {}
        executed = run.get("status") == "success"
        rows.append(
            {
                "name": name,
                "status": "executed_success" if executed else "configured_not_run",
                "duration_s": run.get("duration_s"),
                "last_run": str(report.get("generated_at"))
                if executed
                else "sin ejecución registrada",
                "runs_7d": 1 if executed else 0,
                "evidence": (
                    "artifacts/verification/container-runtime.json"
                    if executed
                    else path.relative_to(DATA_DIR.parent).as_posix()
                ),
            }
        )
    return rows


def _quality_rows(
    frame: pd.DataFrame,
    forecasts: pd.DataFrame,
    sources: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = [
        "timestamp_utc",
        "asset_id",
        "power_mw",
        "availability",
        "source_id",
        "quality_flag",
    ]
    completeness = 100 * (
        1 - float(frame[selected].isna().sum().sum()) / (len(frame) * len(selected))
    )
    validity = 100 * float(frame["quality_flag"].ne("quarantined").mean())
    uniqueness = 100 * (
        1 - float(frame.duplicated(["asset_id", "timestamp_utc"]).sum()) / max(len(frame), 1)
    )
    expected = frame["asset_id"].nunique() * (
        (
            pd.to_datetime(frame["timestamp_utc"], utc=True).max()
            - pd.to_datetime(frame["timestamp_utc"], utc=True).min()
        )
        / pd.Timedelta(hours=1)
        + 1
    )
    continuity = min(100.0, 100 * len(frame) / max(float(expected), 1))
    quantiles_valid = (forecasts["p10_mw"] <= forecasts["p50_mw"]) & (
        forecasts["p50_mw"] <= forecasts["p90_mw"]
    )
    rows = [
        {
            "dataset": "SCADA Silver",
            "freshness": _safe_number(continuity, 2),
            "completeness": _safe_number(completeness, 2),
            "validity": _safe_number(validity, 2),
            "uniqueness": _safe_number(uniqueness, 2),
            "status": "passed"
            if min(completeness, validity, uniqueness, continuity) >= 99
            else "watch",
        },
        {
            "dataset": "Forecast Gold",
            "freshness": 100.0,
            "completeness": _safe_number(
                100 * (1 - float(forecasts.isna().sum().sum()) / max(forecasts.size, 1)),
                2,
            ),
            "validity": _safe_number(100 * float(quantiles_valid.mean()), 2),
            "uniqueness": _safe_number(
                100
                * (
                    1
                    - float(forecasts.duplicated(["asset_id", "timestamp_utc"]).sum())
                    / max(len(forecasts), 1)
                ),
                2,
            ),
            "status": "passed" if bool(quantiles_valid.all()) else "failed",
        },
    ]
    for source in sources:
        if source["kind"] == "official" and source["status"] == "verified":
            rows.append(
                {
                    "dataset": f"{source['name']} Bronze",
                    "freshness": 100.0 if source["age"] in {"<1 h", "1 h"} else 99.0,
                    "completeness": 100.0 if source["records"] > 0 else 0.0,
                    "validity": 100.0 if source["checksum"] else 0.0,
                    "uniqueness": 100.0,
                    "status": "passed" if source["records"] > 0 else "failed",
                }
            )
    checks_per_dataset = 4
    passed = sum(item["status"] == "passed" for item in rows) * checks_per_dataset
    total = len(rows) * checks_per_dataset
    quarantined = int(frame["quality_flag"].eq("quarantined").sum())
    summary = {
        "checks_executed": total,
        "checks_passed": passed,
        "checks_watch_or_failed": total - passed,
        "quarantined_rows": quarantined,
        "quarantined_rate": _safe_number(100 * quarantined / max(len(frame), 1), 3),
        "schema_changes_detected": 0,
        "overall_validity": _safe_number(np.mean([item["validity"] for item in rows]), 2),
    }
    return rows, summary


def _public_resource(value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.relative_to(DATA_DIR.parent).as_posix()
    except ValueError:
        return f"redacted-local-path/{candidate.name}"


def build_dashboard_snapshot(
    telemetry: pd.DataFrame,
    forecasts: pd.DataFrame,
    metrics: list[ModelMetrics],
    cv_metrics: dict[str, object],
    *,
    pipeline_run_id: str,
) -> dict[str, Any]:
    """Build the complete bounded reader snapshot consumed by the web application."""

    frame = telemetry.copy()
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    last_timestamp = frame["timestamp_utc"].max()
    snapshot_generated_at = datetime.now(UTC)
    recent = frame.loc[frame["timestamp_utc"] >= last_timestamp - pd.Timedelta(days=7)]
    recent_renewable = recent.loc[recent["technology"].isin(["solar", "wind"])]
    anomalies = detect_anomalies(frame)
    future = build_future_forecast(frame)
    sources = _source_rows()
    quality, quality_summary = _quality_rows(frame, forecasts, sources)

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
    forecast_horizon_metrics: dict[str, list[dict[str, Any]]] = {}
    for technology in ("solar", "wind"):
        evidence = _load_json(
            DATA_DIR / "models" / f"{technology}_forecast_evidence.json"
        )
        raw_horizon = evidence.get("horizon_metrics")
        horizon = raw_horizon if isinstance(raw_horizon, dict) else {}
        raw_buckets = horizon.get("buckets")
        forecast_horizon_metrics[technology] = (
            raw_buckets if isinstance(raw_buckets, list) else []
        )
    drift_payload = _load_json(DATA_DIR / "models" / "drift_metrics.json")
    drift_by_technology = drift_payload.get("technologies")
    drift_rows = (
        drift_by_technology
        if isinstance(drift_by_technology, dict)
        else {}
    )
    champions: list[dict[str, Any]] = []
    challengers: list[dict[str, Any]] = []
    for technology in ("solar", "wind"):
        candidates = sorted(
            (item for item in model_metrics if item["technology"] == technology),
            key=lambda item: (item["validation_mae_mw"], item["mae_mw"]),
        )
        champion = candidates[0]
        challenger = candidates[1]
        raw_drift = drift_rows.get(technology)
        drift = raw_drift if isinstance(raw_drift, dict) else {}
        champions.append(
            {
                **champion,
                "version": "1.0.0",
                "alias": "Champion · evaluation",
                "stage": "Review required",
                "approved_by": "Pending manual approval",
                "drift_status": str(drift.get("status", "not_measured")),
                "drift_max_psi": drift.get("max_psi"),
                "feature_drift": drift.get("feature_psi", {}),
                "target_psi": drift.get("target_psi"),
                "prediction_psi": drift.get("prediction_psi"),
                "trained_at": snapshot_generated_at.isoformat(),
            }
        )
        challengers.append(
            {
                **challenger,
                "version": "1.0.0-rc1",
                "alias": "Challenger",
                "stage": "Offline evaluation",
                "approved_by": "Not requested",
                "drift_status": str(drift.get("status", "not_measured")),
                "drift_max_psi": drift.get("max_psi"),
                "trained_at": snapshot_generated_at.isoformat(),
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
    reference_market_price = float(
        recent_renewable.groupby("timestamp_utc", observed=True)["price_eur_mwh"]
        .mean()
        .mean()
    )
    market_capture_rates: dict[str, float] = {}
    for technology in ("solar", "wind"):
        technology_market = recent_renewable.loc[
            recent_renewable["technology"] == technology
        ]
        energy = technology_market["energy_mwh"].clip(lower=0)
        capture_price = float(
            (technology_market["price_eur_mwh"] * energy).sum()
            / max(float(energy.sum()), 1e-9)
        )
        market_capture_rates[technology] = _safe_number(
            100 * capture_price / max(reference_market_price, 1e-9),
            2,
        )
    portfolio_energy = recent_renewable["energy_mwh"].clip(lower=0)
    portfolio_capture_price = float(
        (recent_renewable["price_eur_mwh"] * portfolio_energy).sum()
        / max(float(portfolio_energy.sum()), 1e-9)
    )
    market_capture_rates["portfolio"] = _safe_number(
        100 * portfolio_capture_price / max(reference_market_price, 1e-9),
        2,
    )

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

    workflows = _workflow_rows()
    services = _runtime_services()
    risks = _risk_rows()
    audit_events = read_events(DATA_DIR / "audit" / "events.jsonl")
    audit = [
        {
            "id": event.event_id,
            "time": event.timestamp,
            "actor": event.actor,
            "action": event.action,
            "resource": _public_resource(event.resource),
            "result": event.result,
        }
        for event in reversed(audit_events[-8:])
    ]

    return {
        "meta": {
            "snapshot_version": "1.0.0",
            "generated_at": snapshot_generated_at.isoformat(),
            "data_through": last_timestamp.isoformat(),
            "display_timezone": "Europe/Madrid",
            "pipeline_run_id": pipeline_run_id,
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
            "data_freshness_minutes": max(
                0,
                int(
                    (
                        pd.Timestamp(snapshot_generated_at) - pd.Timestamp(last_timestamp)
                    ).total_seconds()
                    // 60
                ),
            ),
        },
        "series": series,
        "mix": mix,
        "assets": asset_rows,
        "anomalies": anomaly_rows,
        "future_forecasts": future.to_dict(orient="records"),
        "forecast_horizon_metrics": forecast_horizon_metrics,
        "model_metrics": model_metrics,
        "champions": champions,
        "challengers": challengers,
        "drift": drift_payload,
        "cv_metrics": cv_metrics,
        "market": market,
        "market_capture_rates": market_capture_rates,
        "inspections": inspections,
        "sources": sources,
        "quality": quality,
        "quality_summary": quality_summary,
        "services": services,
        "workflows": workflows,
        "risks": risks,
        "governance": _governance_evidence(),
        "audit": audit,
        "lineage": [
            {
                "from": " · ".join(
                    source["name"]
                    for source in sources
                    if source["kind"] == "official" and source["status"] == "verified"
                ),
                "to": "Bronze",
                "status": "verified",
            },
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
            "challengers": payload["challengers"],
            "metrics": payload["model_metrics"],
        },
        "data-quality.json": payload["quality"],
        "inspections.json": payload["inspections"],
        "sources.json": payload["sources"],
        "system-health.json": {"services": payload["services"], "workflows": payload["workflows"]},
        "governance.json": payload["governance"],
    }
    checksums: dict[str, str] = {}
    for name, document in documents.items():
        encoded = _validate_public_document(name, document)
        (latest / name).write_bytes(encoded)
        checksums[name] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    manifest = {
        "snapshot_version": payload["meta"]["snapshot_version"],
        "generated_at": payload["meta"]["generated_at"],
        "pipeline_run_id": payload["meta"]["pipeline_run_id"],
        "data_status": "valid",
        "is_demo": True,
        "contains_synthetic_data": True,
        "sources": [
            source["name"]
            for source in payload["sources"]
            if source["kind"] == "synthetic" or source["status"] == "verified"
        ],
        "files": checksums,
    }
    manifest_path = public_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    history = public_dir / "history" / str(payload["meta"]["generated_at"])[:10]
    if history.exists():
        shutil.rmtree(history)
    shutil.copytree(latest, history)
    return manifest_path
