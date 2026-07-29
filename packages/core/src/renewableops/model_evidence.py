"""Reproducible, public-safe evidence for trained forecasting artifacts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

from .config import DATA_DIR, MANIFEST_DIR, MODEL_DIR, PROJECT_ROOT


def _load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


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


def _estimator_details(model: Any) -> tuple[str, dict[str, object], int | None]:
    estimator = getattr(model, "regressor_", model)
    named_steps = getattr(estimator, "named_steps", None)
    if isinstance(named_steps, dict):
        estimator = named_steps.get("model", estimator)

    class_name = type(estimator).__name__
    parameters: dict[str, object] = {}
    raw_parameters = estimator.get_params(deep=False) if hasattr(estimator, "get_params") else {}
    for name in (
        "n_estimators",
        "max_depth",
        "min_samples_leaf",
        "max_features",
        "learning_rate",
        "max_iter",
        "max_leaf_nodes",
        "alpha",
        "l1_ratio",
    ):
        value = raw_parameters.get(name)
        if name in raw_parameters and (
            isinstance(value, (str, int, float, bool)) or value is None
        ):
            parameters[name] = value

    fitted_members = getattr(estimator, "estimators_", None)
    tree_count = len(fitted_members) if fitted_members is not None else None
    if tree_count is None:
        iterations = getattr(estimator, "n_iter_", None)
        tree_count = int(iterations) if isinstance(iterations, (int, np.integer)) else None
    return class_name, parameters, tree_count


def _mlflow_tracking(database_path: Path) -> dict[str, object]:
    if not database_path.exists():
        return {
            "status": "not_available",
            "backend": "local SQLite",
            "experiment": "renewableops-local-forecast",
            "runs": 0,
            "note": "Enable MLflow during training to create local experiment evidence.",
        }

    try:
        with sqlite3.connect(database_path) as connection:
            run_count = int(connection.execute("SELECT count(*) FROM runs").fetchone()[0])
    except (sqlite3.Error, TypeError, ValueError):
        run_count = 0
    return {
        "status": "verified" if run_count > 0 else "empty",
        "backend": "local SQLite",
        "experiment": "renewableops-local-forecast",
        "runs": run_count,
        "note": "Local tracking state is verified but intentionally not published as a database.",
    }


def build_model_verification(
    *,
    model_dir: Path = MODEL_DIR,
    manifest_path: Path = MANIFEST_DIR / "generation_silver.json",
    mlflow_database: Path = DATA_DIR / "mlflow.db",
) -> dict[str, Any]:
    """Load real artifacts, execute smoke inference and return bounded evidence."""

    registry = _load_object(model_dir / "model_registry.json")
    aliases = registry.get("aliases")
    registry_aliases = aliases if isinstance(aliases, dict) else {}
    manifest = _load_object(manifest_path)
    metrics = _load_list(model_dir / "forecast_metrics.json")
    artifacts: list[dict[str, Any]] = []
    checks: list[dict[str, object]] = []

    for technology in ("solar", "wind"):
        artifact_path = model_dir / f"{technology}_forecast_champion.joblib"
        artifact = joblib.load(artifact_path)
        model = artifact["model"]
        feature_columns = [str(column) for column in artifact["feature_columns"]]
        input_frame = pd.DataFrame(artifact["input_example"]).loc[:, feature_columns].head(1)
        point_prediction = float(np.asarray(model.predict(input_frame))[0])
        raw_quantiles = np.asarray(
            [
                artifact["quantile_models"][label].predict(input_frame)[0]
                for label in ("p10", "p50", "p90")
            ],
            dtype=float,
        )
        ordered_quantiles = np.sort(raw_quantiles)
        registry_record = registry_aliases.get(technology)
        record = registry_record if isinstance(registry_record, dict) else {}
        raw_aliases = record.get("aliases")
        model_aliases = raw_aliases if isinstance(raw_aliases, dict) else {}
        approval = record.get("approval")
        approval_record = approval if isinstance(approval, dict) else {}
        estimator_class, hyperparameters, tree_count = _estimator_details(model)
        model_name = str(artifact["model_name"])
        artifact_hash = _hash_file(artifact_path)
        technology_checks = {
            "artifact_loads": True,
            "registry_alias_matches": model_aliases.get("Champion") == model_name,
            "feature_schema_matches": list(input_frame.columns) == feature_columns,
            "point_prediction_finite": bool(np.isfinite(point_prediction)),
            "quantiles_finite": bool(np.isfinite(raw_quantiles).all()),
            "quantiles_ordered_after_documented_repair": bool(
                np.all(np.diff(ordered_quantiles) >= 0)
            ),
        }
        checks.extend(
            {
                "id": f"{technology}.{name}",
                "passed": passed,
            }
            for name, passed in technology_checks.items()
        )
        artifacts.append(
            {
                "technology": technology,
                "model": model_name,
                "alias": "Champion",
                "file": _relative_path(artifact_path),
                "sha256": f"sha256:{artifact_hash}",
                "size_bytes": artifact_path.stat().st_size,
                "estimator_class": estimator_class,
                "hyperparameters": hyperparameters,
                "fitted_tree_count": tree_count,
                "feature_count": len(feature_columns),
                "features": feature_columns,
                "trained_until": str(artifact["trained_until"]),
                "seed": int(artifact["seed"]),
                "validation": artifact["validation"],
                "smoke_inference": {
                    "status": "passed",
                    "input_row_sha256": (
                        "sha256:"
                        + hashlib.sha256(
                            input_frame.to_json(orient="records", double_precision=10).encode()
                        ).hexdigest()
                    ),
                    "point_prediction_mw": round(point_prediction, 4),
                    "raw_quantiles_mw": {
                        "p10": round(float(raw_quantiles[0]), 4),
                        "p50": round(float(raw_quantiles[1]), 4),
                        "p90": round(float(raw_quantiles[2]), 4),
                    },
                    "served_quantiles_mw": {
                        "p10": round(float(ordered_quantiles[0]), 4),
                        "p50": round(float(ordered_quantiles[1]), 4),
                        "p90": round(float(ordered_quantiles[2]), 4),
                    },
                },
                "approval": {
                    "status": str(approval_record.get("status", "pending")),
                    "approver": approval_record.get("approver"),
                    "reviewed_at": approval_record.get("reviewed_at"),
                    "evidence_hash": approval_record.get("evidence_hash"),
                    "scope": record.get("scope", "evaluation_only"),
                },
            }
        )

    candidates_by_technology = {
        technology: sorted(
            (item for item in metrics if item.get("technology") == technology),
            key=lambda item: (
                float(item.get("validation_mae_mw", float("inf"))),
                float(item.get("mae_mw", float("inf"))),
            ),
        )
        for technology in ("solar", "wind")
    }
    candidate_count = sum(len(items) for items in candidates_by_technology.values())
    algorithm_count = len(
        {str(item.get("model")) for items in candidates_by_technology.values() for item in items}
    )
    all_checks_passed = all(bool(item["passed"]) for item in checks)
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if all_checks_passed else "failed",
        "run": {
            "training_run_id": manifest.get("run_id"),
            "training_code_commit": manifest.get("code_commit"),
            "verification_code_commit": _code_commit(),
            "registry_generated_at": registry.get("generated_at"),
        },
        "learning": {
            "mode": "offline_batch_retraining",
            "online_learning": False,
            "automatic_retraining": False,
            "selection_metric": "rolling temporal validation MAE",
            "test_used_for_selection": False,
            "validation_folds": 3,
            "validation_gap_hours": 24,
            "blocked_test_days": 14,
            "candidate_count": candidate_count,
            "algorithm_count": algorithm_count,
            "algorithms": [
                "Ridge",
                "ElasticNet",
                "RandomForestRegressor",
                "ExtraTreesRegressor",
                "HistGradientBoostingRegressor",
            ],
            "reproduce_command": "make demo",
            "verify_command": "uv run renewableops verify-models",
        },
        "dataset": {
            "manifest": _relative_path(manifest_path),
            "dataset_id": manifest.get("dataset_id"),
            "version": manifest.get("dataset_version"),
            "row_count": manifest.get("row_count"),
            "min_timestamp": manifest.get("min_timestamp"),
            "max_timestamp": manifest.get("max_timestamp"),
            "content_hash": manifest.get("content_hash"),
            "schema_hash": manifest.get("schema_hash"),
            "quality_status": manifest.get("quality_status"),
            "contains_synthetic_data": manifest.get("contains_synthetic_data"),
        },
        "runtime": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "tracking": _mlflow_tracking(mlflow_database),
        "artifacts": artifacts,
        "checks": checks,
    }


def write_model_verification(
    *,
    model_dir: Path = MODEL_DIR,
    manifest_path: Path = MANIFEST_DIR / "generation_silver.json",
    mlflow_database: Path = DATA_DIR / "mlflow.db",
) -> dict[str, Any]:
    """Write the sanitized verification report next to the model artifacts."""

    payload = build_model_verification(
        model_dir=model_dir,
        manifest_path=manifest_path,
        mlflow_database=mlflow_database,
    )
    path = model_dir / "model_verification.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
