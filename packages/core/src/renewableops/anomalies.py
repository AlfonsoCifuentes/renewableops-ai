"""Layered physical, residual and Isolation Forest anomaly detection."""

from __future__ import annotations

import os

# Isolation Forest is intentionally single-threaded in the demo. This avoids a
# noisy physical-core probe on current Windows installations without WMIC.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from .config import DEFAULT_SEED


def detect_anomalies(telemetry: pd.DataFrame, *, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Score recent renewable telemetry and return actionable incident records."""

    renewable = telemetry.loc[telemetry["technology"].isin(["solar", "wind"])].copy()
    renewable["residual_mw"] = renewable["power_mw"] - renewable["expected_power_mw"]
    renewable["residual_ratio"] = renewable["residual_mw"] / renewable[
        "installed_capacity_mw"
    ].clip(lower=1)
    features = renewable[
        ["residual_ratio", "availability", "temperature_c", "wind_speed_ms"]
    ].replace([np.inf, -np.inf], np.nan)
    features = features.fillna(features.median(numeric_only=True))
    scaled = RobustScaler().fit_transform(features)
    detector = IsolationForest(
        n_estimators=100,
        contamination=0.018,
        random_state=seed,
        n_jobs=1,
    )
    renewable["isolation_score"] = -detector.fit_predict(scaled)
    renewable["residual_alert"] = renewable["residual_ratio"] < -0.14
    renewable["is_anomaly"] = (
        (renewable["isolation_score"] > 0)
        | renewable["residual_alert"]
        | (renewable["anomaly_type"] != "none")
    )
    recent_cutoff = pd.to_datetime(renewable["timestamp_utc"], utc=True).max() - pd.Timedelta(
        days=14
    )
    flagged = renewable.loc[
        renewable["is_anomaly"]
        & (pd.to_datetime(renewable["timestamp_utc"], utc=True) >= recent_cutoff)
    ].copy()
    if flagged.empty:
        return flagged
    grouped = (
        flagged.groupby(["asset_id", "asset_name", "technology"], observed=True)
        .agg(
            started_at=("timestamp_utc", "min"),
            last_seen_at=("timestamp_utc", "max"),
            points=("timestamp_utc", "size"),
            worst_residual_mw=("residual_mw", "min"),
            capacity_mw=("installed_capacity_mw", "first"),
            labelled_cause=(
                "anomaly_type",
                lambda value: next((v for v in value if v != "none"), "underperformance"),
            ),
        )
        .reset_index()
    )
    grouped["mwh_at_risk"] = (-grouped["worst_residual_mw"] * grouped["points"]).clip(lower=0)
    grouped["severity"] = np.select(
        [
            grouped["mwh_at_risk"] > 55,
            grouped["mwh_at_risk"] > 18,
            grouped["mwh_at_risk"] > 5,
        ],
        ["critical", "high", "medium"],
        default="low",
    )
    grouped["status"] = "open"
    grouped["confidence"] = np.clip(
        0.62 + grouped["mwh_at_risk"] / grouped["capacity_mw"] / 8, 0.62, 0.98
    )
    grouped["incident_id"] = [f"INC-{index + 241:04d}" for index in range(len(grouped))]
    grouped["recommended_action"] = (
        grouped["labelled_cause"]
        .map(
            {
                "soiling": "Schedule thermographic inspection and verify soiling ratio",
                "yaw_misalignment": "Inspect yaw calibration during next safe access window",
                "frozen_sensor": "Quarantine sensor signal and use fallback weather feature",
                "underperformance": "Review residual evidence and operational alarms",
            }
        )
        .fillna("Review residual evidence and operational alarms")
    )
    return grouped.sort_values(
        ["mwh_at_risk", "last_seen_at"], ascending=[False, False], ignore_index=True
    )
