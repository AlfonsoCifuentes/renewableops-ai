"""Data and prediction drift evidence for the local model review workflow."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import MODEL_DIR
from .features import FEATURE_COLUMNS, build_features

NON_ACTIONABLE_CALENDAR_FEATURES = {"hour_sin", "hour_cos", "day_sin", "day_cos"}


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    """Compute PSI with reference quantile bins and bounded smoothing."""

    reference_values = np.asarray(reference, dtype=float)
    current_values = np.asarray(current, dtype=float)
    reference_values = reference_values[np.isfinite(reference_values)]
    current_values = current_values[np.isfinite(current_values)]
    if len(reference_values) < bins or len(current_values) < bins:
        return 0.0
    edges = np.unique(np.quantile(reference_values, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_histogram, _ = np.histogram(reference_values, bins=edges)
    current_histogram, _ = np.histogram(current_values, bins=edges)
    reference_share = np.clip(reference_histogram / reference_histogram.sum(), 1e-6, None)
    current_share = np.clip(current_histogram / current_histogram.sum(), 1e-6, None)
    return float(
        np.sum(
            (current_share - reference_share)
            * np.log(current_share / reference_share)
        )
    )


def _status(maximum_psi: float) -> str:
    if maximum_psi >= 0.25:
        return "alert"
    if maximum_psi >= 0.10:
        return "watch"
    return "stable"


def compute_drift_report(
    telemetry: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    output_path: Path = MODEL_DIR / "drift_metrics.json",
) -> dict[str, object]:
    """Compare reference and current temporal windows without fitting a model."""

    featured = build_features(telemetry)
    featured["timestamp_utc"] = pd.to_datetime(featured["timestamp_utc"], utc=True)
    predictions_copy = predictions.copy()
    predictions_copy["timestamp_utc"] = pd.to_datetime(
        predictions_copy["timestamp_utc"],
        utc=True,
    )
    technologies: dict[str, object] = {}
    for technology in ("solar", "wind"):
        subset = featured.loc[featured["technology"] == technology].dropna(
            subset=FEATURE_COLUMNS
        )
        end = subset["timestamp_utc"].max()
        cutoff = end - pd.Timedelta(days=14)
        reference_start = cutoff - pd.Timedelta(days=28)
        reference = subset.loc[
            (subset["timestamp_utc"] >= reference_start)
            & (subset["timestamp_utc"] < cutoff)
        ]
        current = subset.loc[subset["timestamp_utc"] >= cutoff]
        feature_psi = {
            column: round(
                population_stability_index(
                    reference[column].to_numpy(),
                    current[column].to_numpy(),
                ),
                5,
            )
            for column in FEATURE_COLUMNS
        }
        normalized_reference = (
            reference["power_mw"] / reference["installed_capacity_mw"]
        ).to_numpy()
        normalized_current = (
            current["power_mw"] / current["installed_capacity_mw"]
        ).to_numpy()
        target_psi = population_stability_index(
            normalized_reference,
            normalized_current,
        )
        technology_predictions = predictions_copy.loc[
            predictions_copy["technology"] == technology
        ].sort_values("timestamp_utc")
        midpoint = max(1, len(technology_predictions) // 2)
        normalized_prediction = (
            technology_predictions["p50_mw"]
            / technology_predictions["installed_capacity_mw"]
        ).to_numpy()
        prediction_psi = population_stability_index(
            normalized_prediction[:midpoint],
            normalized_prediction[midpoint:],
        )
        actionable_feature_psi = {
            name: value
            for name, value in feature_psi.items()
            if name not in NON_ACTIONABLE_CALENDAR_FEATURES
        }
        maximum = max(
            [*actionable_feature_psi.values(), target_psi, prediction_psi]
        )
        technologies[technology] = {
            "status": _status(maximum),
            "max_psi": round(maximum, 5),
            "feature_psi": feature_psi,
            "status_scope": (
                "operational features, normalized target and prediction; "
                "deterministic calendar encodings are informational"
            ),
            "target_psi": round(target_psi, 5),
            "prediction_psi": round(prediction_psi, 5),
            "reference_rows": len(reference),
            "current_rows": len(current),
            "reference_window_days": 28,
            "current_window_days": 14,
            "thresholds": {"watch": 0.10, "alert": 0.25},
        }
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "method": "Population Stability Index with reference-decile bins",
        "scope": (
            "immediately preceding reference window vs current synthetic demo telemetry; "
            "monitoring evidence, not causal diagnosis"
        ),
        "technologies": technologies,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
