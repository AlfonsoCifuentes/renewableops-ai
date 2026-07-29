"""Portable champion/challenger registry with optional MLflow mirroring."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .modeling import ModelMetrics


def write_registry(
    metrics: list[ModelMetrics],
    *,
    model_dir: Path,
    dataset_manifest: str,
) -> Path:
    """Persist reviewable aliases and deterministic promotion gates."""

    aliases: dict[str, dict[str, Any]] = {}
    for technology in ("solar", "wind"):
        ranked = sorted(
            (item for item in metrics if item.technology == technology),
            key=lambda item: (item.validation_mae_mw, item.mae_mw),
        )
        champion = ranked[0]
        challenger = ranked[1]
        gates = {
            "positive_skill_vs_persistence": champion.skill_vs_persistence > 0,
            "nmae_below_10_percent": champion.nmae < 0.10,
            "interval_coverage_recorded": champion.coverage_p10_p90 > 0,
            "manual_approval_required": True,
        }
        aliases[technology] = {
            "model_name": f"{technology}_forecast",
            "scope": "evaluation_only",
            "aliases": {
                "Champion": champion.model,
                "Challenger": challenger.model,
            },
            "champion_metrics": asdict(champion),
            "gates": gates,
            "selection": {
                "metric": "rolling_validation_mae_mw",
                "value": champion.validation_mae_mw,
                "test_used_for_selection": False,
                "validation_folds": champion.validation_folds,
                "gap_hours": champion.validation_gap_hours,
            },
            "promotion_status": "review_required",
            "approval": {
                "status": "pending",
                "required": True,
                "template": "governance/approvals/model-promotion-template.md",
            },
            "deployment_status": "not_deployed",
            "rollback_alias": "Champion",
        }
    payload = {
        "registry_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_manifest": dataset_manifest,
        "aliases": aliases,
        "automatic_production_promotion": False,
    }
    path = model_dir / "model_registry.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def mirror_metrics_to_mlflow(
    metrics: list[ModelMetrics],
    *,
    dataset_manifest: str,
    model_dir: Path | None = None,
) -> bool:
    """Mirror candidate evidence when MLflow is explicitly enabled.

    The local, cost-free pipeline does not make an outbound tracking connection
    unless ``RENEWABLEOPS_ENABLE_MLFLOW=true`` is set.
    """

    if os.getenv("RENEWABLEOPS_ENABLE_MLFLOW", "false").lower() != "true":
        return False
    try:
        import joblib
        import mlflow
        import mlflow.sklearn
        import pandas as pd
        from mlflow.models import infer_signature
    except ImportError as error:
        raise RuntimeError("Install the `platform` extra to enable MLflow") from error

    artifact_dir = model_dir or Path("data/models")
    champions = {
        technology: min(
            (item for item in metrics if item.technology == technology),
            key=lambda item: (item.validation_mae_mw, item.mae_mw),
        ).model
        for technology in ("solar", "wind")
    }
    mlflow.set_experiment("renewableops-local-forecast")
    for item in metrics:
        with mlflow.start_run(run_name=f"{item.technology}-{item.model}"):
            mlflow.log_params(
                {
                    "technology": item.technology,
                    "algorithm": item.model,
                    "split": "blocked_last_14_days",
                    "selection": "TimeSeriesSplit",
                    "validation_folds": item.validation_folds,
                    "validation_gap_hours": item.validation_gap_hours,
                    "dataset_manifest": dataset_manifest,
                }
            )
            mlflow.log_metrics(
                {
                    key: float(value)
                    for key, value in asdict(item).items()
                    if isinstance(value, (float, int)) and key not in {"dataset_rows", "test_rows"}
                }
            )
            mlflow.log_metrics(
                {
                    "dataset_rows": float(item.dataset_rows),
                    "test_rows": float(item.test_rows),
                }
            )
            mlflow.set_tag("contains_synthetic_data", "true")
            mlflow.set_tag("promotion_scope", "evaluation_only")
            evidence = artifact_dir / f"{item.technology}_forecast_evidence.json"
            if evidence.exists():
                mlflow.log_artifact(str(evidence), artifact_path="evidence")
            manifest_path = Path(dataset_manifest)
            if manifest_path.exists():
                mlflow.log_artifact(str(manifest_path), artifact_path="dataset")
            if item.model == champions[item.technology]:
                artifact = joblib.load(
                    artifact_dir / f"{item.technology}_forecast_champion.joblib"
                )
                input_example = pd.DataFrame(artifact["input_example"])
                signature = infer_signature(
                    input_example,
                    artifact["model"].predict(input_example),
                )
                mlflow.sklearn.log_model(
                    sk_model=artifact["model"],
                    name="point_forecaster",
                    signature=signature,
                    input_example=input_example,
                    serialization_format="cloudpickle",
                )
                mlflow.set_tag("candidate_alias", "Champion")
    return True
