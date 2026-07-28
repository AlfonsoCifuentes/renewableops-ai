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
            key=lambda item: item.mae_mw,
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
            "aliases": {
                "Champion": champion.model,
                "Challenger": challenger.model,
            },
            "champion_metrics": asdict(champion),
            "gates": gates,
            "promotion_status": "approved_for_demo",
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


def mirror_metrics_to_mlflow(metrics: list[ModelMetrics], *, dataset_manifest: str) -> bool:
    """Mirror candidate evidence when MLflow is explicitly enabled.

    The local, cost-free pipeline does not make an outbound tracking connection
    unless ``RENEWABLEOPS_ENABLE_MLFLOW=true`` is set.
    """

    if os.getenv("RENEWABLEOPS_ENABLE_MLFLOW", "false").lower() != "true":
        return False
    try:
        import mlflow
    except ImportError as error:
        raise RuntimeError("Install the `platform` extra to enable MLflow") from error

    mlflow.set_experiment("renewableops-local-forecast")
    for item in metrics:
        with mlflow.start_run(run_name=f"{item.technology}-{item.model}"):
            mlflow.log_params(
                {
                    "technology": item.technology,
                    "algorithm": item.model,
                    "split": "blocked_last_14_days",
                    "dataset_manifest": dataset_manifest,
                }
            )
            mlflow.log_metrics(
                {
                    "mae_mw": item.mae_mw,
                    "rmse_mw": item.rmse_mw,
                    "nmae": item.nmae,
                    "bias_mw": item.bias_mw,
                    "skill_vs_persistence": item.skill_vs_persistence,
                    "coverage_p10_p90": item.coverage_p10_p90,
                }
            )
            mlflow.set_tag("contains_synthetic_data", "true")
    return True
