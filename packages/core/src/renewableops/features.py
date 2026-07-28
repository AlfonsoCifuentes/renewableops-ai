"""Leakage-safe feature engineering implemented with Pandas and NumPy."""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "irradiance_wm2",
    "temperature_c",
    "cloud_cover_fraction",
    "wind_speed_ms",
    "availability",
    "lag_24h_mw",
    "rolling_24h_mw",
]


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a new frame with causal lags and cyclical calendar features."""

    result = frame.sort_values(["asset_id", "timestamp_utc"]).copy()
    timestamps = pd.to_datetime(result["timestamp_utc"], utc=True)
    hour = timestamps.dt.hour.to_numpy()
    day = timestamps.dt.dayofyear.to_numpy()
    result["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    result["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    result["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    result["day_cos"] = np.cos(2 * np.pi * day / 365.25)
    grouped = result.groupby("asset_id", observed=True)["power_mw"]
    result["lag_24h_mw"] = grouped.shift(24)
    result["rolling_24h_mw"] = grouped.transform(
        lambda values: values.shift(1).rolling(24, min_periods=6).mean()
    )
    return result
