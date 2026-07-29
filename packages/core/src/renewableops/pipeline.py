"""End-to-end local demo pipeline: Bronze, Silver, Gold, models and snapshots."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .audit import append_event
from .config import LAKEHOUSE_DIR, MANIFEST_DIR, PROJECT_ROOT, ensure_directories
from .modeling import ModelMetrics, train_forecasters
from .monitoring import compute_drift_report
from .registry import mirror_metrics_to_mlflow, write_registry
from .snapshots import build_dashboard_snapshot, publish_snapshot
from .synthetic import generate_scada
from .vision import train_cv_baseline


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _code_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _manifest(
    dataset_id: str,
    path: Path,
    frame: pd.DataFrame,
    *,
    run_id: str,
) -> dict[str, Any]:
    timestamps = pd.to_datetime(frame["timestamp_utc"], utc=True)
    return {
        "dataset_id": dataset_id,
        "dataset_version": datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ"),
        "run_id": run_id,
        "source_ids": sorted(frame["source_id"].unique().tolist()),
        "row_count": len(frame),
        "min_timestamp": timestamps.min().isoformat(),
        "max_timestamp": timestamps.max().isoformat(),
        "schema_hash": hashlib.sha256(
            json.dumps(
                {column: str(dtype) for column, dtype in frame.dtypes.items()}, sort_keys=True
            ).encode()
        ).hexdigest(),
        "content_hash": f"sha256:{_hash_file(path)}",
        "code_commit": _code_commit(),
        "quality_status": "passed",
        "contains_synthetic_data": bool(frame["is_synthetic"].any()),
    }


def clean_silver(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize types, remove duplicates and quarantine impossible values."""

    result = frame.copy()
    result["timestamp_utc"] = pd.to_datetime(result["timestamp_utc"], utc=True)
    result = result.drop_duplicates(subset=["asset_id", "timestamp_utc"], keep="last")
    impossible = (
        (result["availability"] < 0)
        | (result["availability"] > 1)
        | (result["power_mw"] > result["installed_capacity_mw"] * 1.03)
        | ((result["technology"] != "battery") & (result["power_mw"] < -0.001))
    )
    result.loc[impossible, "quality_flag"] = "quarantined"
    numeric = [
        "power_mw",
        "expected_power_mw",
        "availability",
        "irradiance_wm2",
        "temperature_c",
        "cloud_cover_fraction",
        "wind_speed_ms",
        "price_eur_mwh",
    ]
    result[numeric] = result.groupby("asset_id", observed=True)[numeric].transform(
        lambda values: values.interpolate(limit=3).ffill(limit=1)
    )
    return result.sort_values(["timestamp_utc", "asset_id"], ignore_index=True)


def run_demo_pipeline(*, days: int = 90) -> dict[str, Any]:
    """Execute a bounded, fully reproducible local portfolio pipeline."""

    ensure_directories()
    started_at = datetime.now(UTC)
    correlation_id = f"run-{started_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    audit_path = LAKEHOUSE_DIR.parent / "audit" / "events.jsonl"
    bronze = generate_scada(days=days)
    bronze_path = LAKEHOUSE_DIR / "bronze" / "synthetic_scada.parquet"
    bronze.to_parquet(bronze_path, index=False, compression="zstd")
    silver = clean_silver(bronze)
    silver_path = LAKEHOUSE_DIR / "silver" / "generation.parquet"
    silver.to_parquet(silver_path, index=False, compression="zstd")
    append_event(
        audit_path,
        actor="local-pipeline",
        action="DATA_INGESTED",
        resource="generation_silver",
        resource_version=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        result="success",
        correlation_id=correlation_id,
        metadata={"rows": len(silver), "synthetic": True},
    )
    predictions, metrics = train_forecasters(silver)
    drift_report = compute_drift_report(silver, predictions)
    registry_path = write_registry(
        metrics,
        model_dir=LAKEHOUSE_DIR.parent / "models",
        dataset_manifest="data/manifests/generation_silver.json",
    )
    mlflow_mirrored = mirror_metrics_to_mlflow(
        metrics,
        dataset_manifest="data/manifests/generation_silver.json",
    )
    gold_path = LAKEHOUSE_DIR / "gold" / "forecast_evaluation.parquet"
    predictions.to_parquet(gold_path, index=False, compression="zstd")
    cv_metrics = train_cv_baseline()
    append_event(
        audit_path,
        actor="local-pipeline",
        action="MODEL_TRAINED",
        resource="forecast_champions",
        resource_version="1.0.0",
        result="success",
        correlation_id=correlation_id,
        metadata={"candidate_count": len(metrics)},
    )
    dashboard = build_dashboard_snapshot(
        silver,
        predictions,
        metrics,
        cv_metrics,
        pipeline_run_id=correlation_id,
    )
    manifest_path = publish_snapshot(dashboard)
    snapshot_event = append_event(
        audit_path,
        actor="local-pipeline",
        action="SNAPSHOT_PUBLISHED",
        resource=manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        resource_version=dashboard["meta"]["snapshot_version"],
        result="success",
        correlation_id=correlation_id,
        metadata={"public_demo": True},
    )
    for dataset_id, path, frame in (
        ("synthetic_scada_bronze", bronze_path, bronze),
        ("generation_silver", silver_path, silver),
        (
            "forecast_evaluation_gold",
            gold_path,
            predictions.assign(source_id="sklearn", is_synthetic=True),
        ),
    ):
        manifest = _manifest(dataset_id, path, frame, run_id=correlation_id)
        (MANIFEST_DIR / f"{dataset_id}.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    return {
        "rows": len(silver),
        "assets": silver["asset_id"].nunique(),
        "models": [asdict(item) for item in metrics],
        "snapshot_manifest": str(manifest_path),
        "audit_event_id": snapshot_event.event_id,
        "model_registry": str(registry_path),
        "mlflow_mirrored": mlflow_mirrored,
        "drift": drift_report,
    }


def refresh_public_snapshot() -> dict[str, Any]:
    """Republish from versioned data/model artifacts without retraining."""

    ensure_directories()
    required = {
        "silver": LAKEHOUSE_DIR / "silver" / "generation.parquet",
        "gold": LAKEHOUSE_DIR / "gold" / "forecast_evaluation.parquet",
        "metrics": LAKEHOUSE_DIR.parent / "models" / "forecast_metrics.json",
        "cv": LAKEHOUSE_DIR.parent / "models" / "cv_metrics.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Cannot refresh snapshot; missing versioned artifacts: {', '.join(missing)}"
        )
    started_at = datetime.now(UTC)
    correlation_id = f"snapshot-{started_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    telemetry = pd.read_parquet(required["silver"])
    predictions = pd.read_parquet(required["gold"])
    metrics_payload: object = json.loads(required["metrics"].read_text(encoding="utf-8"))
    if not isinstance(metrics_payload, list):
        raise ValueError("forecast_metrics.json must contain a list")
    metrics = [
        ModelMetrics(**item)
        for item in metrics_payload
        if isinstance(item, dict)
    ]
    cv_payload: object = json.loads(required["cv"].read_text(encoding="utf-8"))
    if not isinstance(cv_payload, dict):
        raise ValueError("cv_metrics.json must contain an object")
    dashboard = build_dashboard_snapshot(
        telemetry,
        predictions,
        metrics,
        cv_payload,
        pipeline_run_id=correlation_id,
    )
    manifest_path = publish_snapshot(dashboard)
    event = append_event(
        LAKEHOUSE_DIR.parent / "audit" / "events.jsonl",
        actor="snapshot-refresh",
        action="SNAPSHOT_PUBLISHED",
        resource=manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        resource_version=dashboard["meta"]["snapshot_version"],
        result="success",
        correlation_id=correlation_id,
        metadata={"retrained": False, "public_demo": True},
    )
    return {
        "status": "published",
        "retrained": False,
        "pipeline_run_id": correlation_id,
        "snapshot_manifest": str(manifest_path),
        "audit_event_id": event.event_id,
    }
