"""Temporal forecasting baselines, candidates, quantiles and model artifacts."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Windows images without WMIC cannot expose a physical-core count to loky.
# The models deliberately use one worker, so make that bound explicit before
# scikit-learn imports joblib's process backend.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import DEFAULT_SEED, MODEL_DIR
from .features import FEATURE_COLUMNS, build_features


@dataclass(frozen=True)
class ModelMetrics:
    technology: str
    model: str
    mae_mw: float
    rmse_mw: float
    nmae: float
    bias_mw: float
    skill_vs_persistence: float
    coverage_p10_p90: float
    dataset_rows: int
    test_rows: int


def _candidates(seed: int) -> dict[str, Any]:
    linear = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=2.5)),
        ]
    )
    return {
        "ridge": TransformedTargetRegressor(regressor=linear, transformer=StandardScaler()),
        "extra_trees": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=90,
                        min_samples_leaf=3,
                        max_features=0.8,
                        n_jobs=1,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        learning_rate=0.07,
                        max_iter=130,
                        max_leaf_nodes=24,
                        l2_regularization=0.4,
                        random_state=seed,
                    ),
                ),
            ]
        ),
    }


def _metrics(
    technology: str,
    model_name: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    baseline: np.ndarray,
    capacity: np.ndarray,
    p10: np.ndarray,
    p90: np.ndarray,
    dataset_rows: int,
) -> ModelMetrics:
    mae = float(mean_absolute_error(truth, prediction))
    baseline_mae = float(mean_absolute_error(truth, baseline))
    return ModelMetrics(
        technology=technology,
        model=model_name,
        mae_mw=round(mae, 4),
        rmse_mw=round(float(np.sqrt(mean_squared_error(truth, prediction))), 4),
        nmae=round(float(np.mean(np.abs(truth - prediction) / capacity)), 5),
        bias_mw=round(float(np.mean(prediction - truth)), 4),
        skill_vs_persistence=round(1 - mae / baseline_mae, 4) if baseline_mae else 0,
        coverage_p10_p90=round(float(np.mean((truth >= p10) & (truth <= p90))), 4),
        dataset_rows=dataset_rows,
        test_rows=len(truth),
    )


def train_forecasters(
    telemetry: pd.DataFrame,
    *,
    model_dir: Path = MODEL_DIR,
    seed: int = DEFAULT_SEED,
) -> tuple[pd.DataFrame, list[ModelMetrics]]:
    """Train and compare multiple sklearn models using a blocked temporal holdout."""

    model_dir.mkdir(parents=True, exist_ok=True)
    featured = build_features(telemetry)
    metrics: list[ModelMetrics] = []
    predictions: list[pd.DataFrame] = []
    for technology in ("solar", "wind"):
        subset = featured.loc[featured["technology"] == technology].dropna(
            subset=["lag_24h_mw", "rolling_24h_mw"]
        )
        cutoff = pd.to_datetime(subset["timestamp_utc"], utc=True).max() - pd.Timedelta(days=14)
        train = subset.loc[pd.to_datetime(subset["timestamp_utc"], utc=True) < cutoff]
        test = subset.loc[pd.to_datetime(subset["timestamp_utc"], utc=True) >= cutoff]
        x_train, y_train = train[FEATURE_COLUMNS], train["power_mw"].to_numpy()
        x_test, y_test = test[FEATURE_COLUMNS], test["power_mw"].to_numpy()
        baseline = test["lag_24h_mw"].to_numpy()
        fitted: dict[str, Any] = {}
        scored: list[tuple[float, str, np.ndarray]] = []
        for name, candidate in _candidates(seed).items():
            candidate.fit(x_train, y_train)
            predicted = np.asarray(candidate.predict(x_test))
            fitted[name] = candidate
            scored.append((float(mean_absolute_error(y_test, predicted)), name, predicted))
        scored.sort(key=lambda item: item[0])
        _, champion_name, champion_prediction = scored[0]
        residual = y_train - np.asarray(fitted[champion_name].predict(x_train))
        low, high = np.quantile(residual, [0.1, 0.9])
        low = min(float(low), 0.0)
        high = max(float(high), 0.0)
        p50 = np.clip(
            champion_prediction,
            0,
            test["installed_capacity_mw"].to_numpy(),
        )
        p10 = np.minimum(np.clip(champion_prediction + low, 0, None), p50)
        p90 = np.maximum(
            np.minimum(
                champion_prediction + high,
                test["installed_capacity_mw"].to_numpy(),
            ),
            p50,
        )
        for _, name, predicted in scored:
            candidate_p50 = np.clip(predicted, 0, test["installed_capacity_mw"].to_numpy())
            metrics.append(
                _metrics(
                    technology,
                    name,
                    y_test,
                    candidate_p50,
                    baseline,
                    test["installed_capacity_mw"].to_numpy(),
                    np.clip(candidate_p50 + low, 0, None),
                    np.minimum(
                        candidate_p50 + high,
                        test["installed_capacity_mw"].to_numpy(),
                    ),
                    len(subset),
                )
            )
        artifact = {
            "technology": technology,
            "model_name": champion_name,
            "model": fitted[champion_name],
            "feature_columns": FEATURE_COLUMNS,
            "residual_quantiles": (float(low), float(high)),
            "trained_until": cutoff.isoformat(),
            "seed": seed,
        }
        joblib.dump(
            artifact,
            model_dir / f"{technology}_forecast_champion.joblib",
            compress=3,
        )
        output = test[
            [
                "timestamp_utc",
                "asset_id",
                "asset_name",
                "technology",
                "power_mw",
                "installed_capacity_mw",
            ]
        ].copy()
        output["p10_mw"] = p10
        output["p50_mw"] = p50
        output["p90_mw"] = p90
        output["model"] = champion_name
        predictions.append(output)

    metrics_payload = [asdict(item) for item in metrics]
    (model_dir / "forecast_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2), encoding="utf-8"
    )
    return pd.concat(predictions, ignore_index=True), metrics


def build_future_forecast(
    telemetry: pd.DataFrame,
    *,
    hours: int = 48,
) -> pd.DataFrame:
    """Create operational quantile forecasts from learned historical profiles."""

    renewable = telemetry.loc[telemetry["technology"].isin(["solar", "wind"])].copy()
    renewable["timestamp_utc"] = pd.to_datetime(renewable["timestamp_utc"], utc=True)
    last = renewable["timestamp_utc"].max()
    rows: list[dict[str, Any]] = []
    for asset_id, group in renewable.groupby("asset_id", observed=True):
        group = group.sort_values("timestamp_utc")
        capacity = float(group["installed_capacity_mw"].iloc[-1])
        for horizon in range(1, hours + 1):
            target = last + pd.Timedelta(hours=horizon)
            reference_time = target - pd.Timedelta(days=1)
            reference = group.iloc[(group["timestamp_utc"] - reference_time).abs().argsort()[:1]]
            expected = float(reference["expected_power_mw"].iloc[0])
            uncertainty = capacity * (0.045 + 0.0011 * horizon)
            rows.append(
                {
                    "timestamp_utc": target.isoformat(),
                    "asset_id": asset_id,
                    "asset_name": group["asset_name"].iloc[-1],
                    "technology": group["technology"].iloc[-1],
                    "horizon_hours": horizon,
                    "p10_mw": round(max(0, expected - uncertainty), 3),
                    "p50_mw": round(min(capacity, max(0, expected)), 3),
                    "p90_mw": round(min(capacity, max(0, expected + uncertainty)), 3),
                    "model_version": "1.0.0",
                    "is_synthetic": True,
                }
            )
    return pd.DataFrame(rows)
