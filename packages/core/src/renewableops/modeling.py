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
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_pinball_loss, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
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
    validation_mae_mw: float = 0.0
    nrmse: float = 0.0
    pinball_p10: float = 0.0
    pinball_p50: float = 0.0
    pinball_p90: float = 0.0
    interval_width_mw: float = 0.0
    quantile_crossing_rate: float = 0.0
    validation_folds: int = 0
    validation_gap_hours: int = 0


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
        "elastic_net": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                (
                    "model",
                    ElasticNet(
                        alpha=0.015,
                        l1_ratio=0.2,
                        max_iter=3_000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=70,
                        max_depth=16,
                        min_samples_leaf=3,
                        max_features=0.8,
                        n_jobs=1,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=70,
                        max_depth=18,
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
    *,
    validation_mae: float,
    validation_folds: int,
    validation_gap_hours: int,
) -> ModelMetrics:
    mae = float(mean_absolute_error(truth, prediction))
    baseline_mae = float(mean_absolute_error(truth, baseline))
    crossing_rate = float(np.mean(p10 > p90))
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
        validation_mae_mw=round(validation_mae, 4),
        nrmse=round(
            float(np.sqrt(mean_squared_error(truth, prediction)) / np.mean(capacity)),
            5,
        ),
        pinball_p10=round(float(mean_pinball_loss(truth, p10, alpha=0.1)), 4),
        pinball_p50=round(float(mean_pinball_loss(truth, prediction, alpha=0.5)), 4),
        pinball_p90=round(float(mean_pinball_loss(truth, p90, alpha=0.9)), 4),
        interval_width_mw=round(float(np.mean(p90 - p10)), 4),
        quantile_crossing_rate=round(crossing_rate, 5),
        validation_folds=validation_folds,
        validation_gap_hours=validation_gap_hours,
    )


def _temporal_validation_mae(
    candidate: Any,
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    *,
    gap_hours: int,
) -> tuple[float, int]:
    """Score a candidate on rolling temporal folds without touching final test."""

    splitter = TimeSeriesSplit(n_splits=3, gap=gap_hours)
    scores: list[float] = []
    for fit_index, validation_index in splitter.split(x_train):
        candidate.fit(x_train.iloc[fit_index], y_train[fit_index])
        predicted = np.asarray(candidate.predict(x_train.iloc[validation_index]))
        scores.append(float(mean_absolute_error(y_train[validation_index], predicted)))
    return float(np.mean(scores)), len(scores)


def _baseline_predictions(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> dict[str, np.ndarray]:
    """Return the five mandatory, leakage-safe operational baselines."""

    train_copy = train.copy()
    train_copy["hour"] = pd.to_datetime(train_copy["timestamp_utc"], utc=True).dt.hour
    train_copy["weekday"] = pd.to_datetime(train_copy["timestamp_utc"], utc=True).dt.weekday
    hourly = (
        train_copy.groupby(["asset_id", "weekday", "hour"], observed=True)["power_mw"]
        .mean()
        .to_dict()
    )
    fallback = train_copy.groupby("asset_id", observed=True)["power_mw"].mean().to_dict()
    test_times = pd.to_datetime(test["timestamp_utc"], utc=True)
    hour_day = np.array(
        [
            hourly.get(
                (asset_id, timestamp.weekday(), timestamp.hour),
                fallback.get(asset_id, 0.0),
            )
            for asset_id, timestamp in zip(test["asset_id"], test_times, strict=True)
        ],
        dtype=float,
    )
    capacity = test["installed_capacity_mw"].to_numpy()
    return {
        "persistence_1h": test["lag_1h_mw"].to_numpy(),
        "same_hour_24h": test["lag_24h_mw"].to_numpy(),
        "same_hour_168h": test["lag_168h_mw"].to_numpy(),
        "hour_weekday_mean": np.clip(hour_day, 0, capacity),
        "physical_expected_power": np.clip(test["expected_power_mw"].to_numpy(), 0, capacity),
    }


def _fit_quantile_models(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
    *,
    seed: int,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, float]:
    """Fit independent gradient-boosting quantile models and repair any crossings."""

    fitted: dict[str, Any] = {}
    raw: list[np.ndarray] = []
    for label, alpha in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9)):
        model = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    GradientBoostingRegressor(
                        loss="quantile",
                        alpha=alpha,
                        n_estimators=80,
                        learning_rate=0.06,
                        max_depth=3,
                        min_samples_leaf=8,
                        random_state=seed,
                    ),
                ),
            ]
        )
        model.fit(x_train, y_train)
        fitted[label] = model
        raw.append(np.asarray(model.predict(x_test)))
    raw_matrix = np.vstack(raw)
    raw_crossing = float(
        np.mean((raw_matrix[0] > raw_matrix[1]) | (raw_matrix[1] > raw_matrix[2]))
    )
    repaired = np.sort(raw_matrix, axis=0)
    return fitted, repaired[0], repaired[1], repaired[2], raw_crossing


def train_forecasters(
    telemetry: pd.DataFrame,
    *,
    model_dir: Path = MODEL_DIR,
    seed: int = DEFAULT_SEED,
) -> tuple[pd.DataFrame, list[ModelMetrics]]:
    """Train point and quantile models with rolling validation and untouched test."""

    model_dir.mkdir(parents=True, exist_ok=True)
    featured = build_features(telemetry)
    metrics: list[ModelMetrics] = []
    predictions: list[pd.DataFrame] = []
    for technology in ("solar", "wind"):
        subset = featured.loc[featured["technology"] == technology].dropna(
            subset=["lag_1h_mw", "lag_24h_mw", "lag_168h_mw", "rolling_24h_mw"]
        )
        cutoff = pd.to_datetime(subset["timestamp_utc"], utc=True).max() - pd.Timedelta(days=14)
        train = subset.loc[pd.to_datetime(subset["timestamp_utc"], utc=True) < cutoff]
        test = subset.loc[pd.to_datetime(subset["timestamp_utc"], utc=True) >= cutoff]
        x_train, y_train = train[FEATURE_COLUMNS], train["power_mw"].to_numpy()
        x_test, y_test = test[FEATURE_COLUMNS], test["power_mw"].to_numpy()
        baselines = _baseline_predictions(train, test)
        reference_baseline = baselines["same_hour_24h"]
        fitted: dict[str, Any] = {}
        scored: list[tuple[float, str, np.ndarray, int]] = []
        gap_hours = 24
        for name, candidate in _candidates(seed).items():
            validation_mae, folds = _temporal_validation_mae(
                candidate,
                x_train,
                y_train,
                gap_hours=gap_hours,
            )
            candidate.fit(x_train, y_train)
            predicted = np.asarray(candidate.predict(x_test))
            fitted[name] = candidate
            scored.append((validation_mae, name, predicted, folds))
        scored.sort(key=lambda item: item[0])
        champion_validation_mae, champion_name, _, validation_folds = scored[0]
        quantile_models, raw_p10, raw_p50, raw_p90, raw_crossing = _fit_quantile_models(
            x_train,
            y_train,
            x_test,
            seed=seed,
        )
        capacity = test["installed_capacity_mw"].to_numpy()
        p10 = np.clip(raw_p10, 0, capacity)
        p50 = np.clip(raw_p50, 0, capacity)
        p90 = np.clip(raw_p90, 0, capacity)
        repaired = np.sort(np.vstack([p10, p50, p90]), axis=0)
        p10, p50, p90 = repaired[0], repaired[1], repaired[2]
        for validation_mae, name, predicted, folds in scored:
            candidate_p50 = np.clip(predicted, 0, test["installed_capacity_mw"].to_numpy())
            metrics.append(
                _metrics(
                    technology,
                    name,
                    y_test,
                    candidate_p50,
                    reference_baseline,
                    test["installed_capacity_mw"].to_numpy(),
                    p10,
                    p90,
                    len(subset),
                    validation_mae=validation_mae,
                    validation_folds=folds,
                    validation_gap_hours=gap_hours,
                )
            )
        baseline_metrics = {
            name: {
                "mae_mw": round(float(mean_absolute_error(y_test, values)), 4),
                "rmse_mw": round(
                    float(np.sqrt(mean_squared_error(y_test, values))),
                    4,
                ),
            }
            for name, values in baselines.items()
        }
        artifact = {
            "technology": technology,
            "model_name": champion_name,
            "model": fitted[champion_name],
            "quantile_models": quantile_models,
            "feature_columns": FEATURE_COLUMNS,
            "input_example": x_train.head(5).to_dict(orient="records"),
            "validation": {
                "method": "TimeSeriesSplit",
                "folds": validation_folds,
                "gap_hours": gap_hours,
                "selection_metric": "MAE",
                "selection_score": champion_validation_mae,
                "test_is_untouched_for_selection": True,
            },
            "baselines": baseline_metrics,
            "raw_quantile_crossing_rate": raw_crossing,
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
        output["forecast_issue_time"] = cutoff.isoformat()
        output["horizon_hours"] = (
            (
                pd.to_datetime(output["timestamp_utc"], utc=True)
                - pd.to_datetime(cutoff, utc=True)
            )
            .dt.total_seconds()
            .div(3600)
            .astype(int)
            .clip(lower=1, upper=336)
        )
        predictions.append(output)
        horizon_bins = (
            ("0–6 h", 1, 6),
            ("7–12 h", 7, 12),
            ("13–18 h", 13, 18),
            ("19–24 h", 19, 24),
            ("25–36 h", 25, 36),
            ("37–48 h", 37, 48),
        )
        horizon_metrics = []
        absolute_error = np.abs(
            output["power_mw"].to_numpy(dtype=float)
            - output["p50_mw"].to_numpy(dtype=float)
        )
        for label, start, end in horizon_bins:
            mask = output["horizon_hours"].between(start, end).to_numpy()
            horizon_metrics.append(
                {
                    "label": label,
                    "start_hour": start,
                    "end_hour": end,
                    "mae_mw": round(float(np.mean(absolute_error[mask])), 4),
                    "observations": int(mask.sum()),
                }
            )

        evidence_path = model_dir / f"{technology}_forecast_evidence.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "technology": technology,
                    "selected_model": champion_name,
                    "selected_on": "rolling temporal validation MAE",
                    "test_used_for_selection": False,
                    "validation": artifact["validation"],
                    "baselines": baseline_metrics,
                    "quantiles": {
                        "method": "three GradientBoostingRegressor models",
                        "alphas": [0.1, 0.5, 0.9],
                        "raw_crossing_rate": round(raw_crossing, 6),
                        "presentation_repair": "row-wise monotonic sort then physical clipping",
                    },
                    "postprocessing": {
                        "bounds": "[0, installed_capacity_mw]",
                        "solar_night": (
                            "physical expected-power reference applied in future inference"
                        ),
                        "raw_and_adjusted": True,
                    },
                    "horizon_metrics": {
                        "scope": "first 48 hours of untouched blocked test",
                        "prediction": "trained P50 quantile model",
                        "buckets": horizon_metrics,
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    metrics_payload = [asdict(item) for item in metrics]
    (model_dir / "forecast_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2), encoding="utf-8"
    )
    return pd.concat(predictions, ignore_index=True), metrics


def build_future_forecast(
    telemetry: pd.DataFrame,
    *,
    hours: int = 48,
    model_dir: Path = MODEL_DIR,
) -> pd.DataFrame:
    """Create recursive 1–48 h forecasts with trained point and quantile models."""

    renewable = telemetry.loc[telemetry["technology"].isin(["solar", "wind"])].copy()
    renewable["timestamp_utc"] = pd.to_datetime(renewable["timestamp_utc"], utc=True)
    last = renewable["timestamp_utc"].max()
    rows: list[dict[str, Any]] = []
    for asset_id, group in renewable.groupby("asset_id", observed=True):
        group = group.sort_values("timestamp_utc")
        technology = str(group["technology"].iloc[-1])
        artifact = joblib.load(model_dir / f"{technology}_forecast_champion.joblib")
        capacity = float(group["installed_capacity_mw"].iloc[-1])
        observed_or_predicted = {
            timestamp: float(value)
            for timestamp, value in zip(
                group["timestamp_utc"],
                group["power_mw"],
                strict=True,
            )
        }
        for horizon in range(1, hours + 1):
            target = last + pd.Timedelta(hours=horizon)
            # Weather is not recursively predicted by the power model. Use a
            # same-hour weekly climatology proxy that is available for the
            # complete 48 h horizon instead of snapping day two to the final
            # (midnight) telemetry row.
            reference_time = target - pd.Timedelta(days=7)
            reference = group.iloc[(group["timestamp_utc"] - reference_time).abs().argsort()[:1]]
            hour = target.hour
            day = target.dayofyear
            lag_24 = observed_or_predicted.get(
                target - pd.Timedelta(hours=24),
                float(reference["power_mw"].iloc[0]),
            )
            prior = [
                observed_or_predicted.get(target - pd.Timedelta(hours=offset))
                for offset in range(1, 25)
            ]
            rolling = float(np.mean([value for value in prior if value is not None]))
            feature_row = pd.DataFrame(
                [
                    {
                        "hour_sin": np.sin(2 * np.pi * hour / 24),
                        "hour_cos": np.cos(2 * np.pi * hour / 24),
                        "day_sin": np.sin(2 * np.pi * day / 365.25),
                        "day_cos": np.cos(2 * np.pi * day / 365.25),
                        "irradiance_wm2": float(reference["irradiance_wm2"].iloc[0]),
                        "temperature_c": float(reference["temperature_c"].iloc[0]),
                        "cloud_cover_fraction": float(
                            reference["cloud_cover_fraction"].iloc[0]
                        ),
                        "wind_speed_ms": float(reference["wind_speed_ms"].iloc[0]),
                        "availability": float(reference["availability"].iloc[0]),
                        "lag_1h_mw": float(
                            observed_or_predicted.get(
                                target - pd.Timedelta(hours=1),
                                group["power_mw"].iloc[-1],
                            )
                        ),
                        "lag_24h_mw": lag_24,
                        "lag_168h_mw": float(
                            observed_or_predicted.get(
                                target - pd.Timedelta(hours=168),
                                reference["power_mw"].iloc[0],
                            )
                        ),
                        "rolling_24h_mw": rolling,
                    }
                ],
                columns=artifact["feature_columns"],
            )
            raw_point = float(artifact["model"].predict(feature_row)[0])
            raw_quantiles = np.array(
                [
                    float(artifact["quantile_models"][label].predict(feature_row)[0])
                    for label in ("p10", "p50", "p90")
                ]
            )
            q10, q50, q90 = np.sort(np.clip(raw_quantiles, 0, capacity))
            adjusted_point = float(np.clip(raw_point, 0, capacity))
            physical_expected = float(reference["expected_power_mw"].iloc[0])
            if technology == "solar" and physical_expected <= capacity * 0.002:
                adjusted_point = q10 = q50 = q90 = 0.0
            observed_or_predicted[target] = adjusted_point
            rows.append(
                {
                    "timestamp_utc": target.isoformat(),
                    "asset_id": asset_id,
                    "asset_name": group["asset_name"].iloc[-1],
                    "technology": technology,
                    "horizon_hours": horizon,
                    "raw_point_mw": round(raw_point, 3),
                    "adjusted_point_mw": round(adjusted_point, 3),
                    "p10_mw": round(float(q10), 3),
                    "p50_mw": round(float(q50), 3),
                    "p90_mw": round(float(q90), 3),
                    "model_name": artifact["model_name"],
                    "model_version": "1.0.0",
                    "is_synthetic": True,
                }
            )
    return pd.DataFrame(rows)
