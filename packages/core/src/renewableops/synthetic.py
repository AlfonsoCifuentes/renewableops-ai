"""Vectorized, deterministic SCADA generation with labelled failure scenarios."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import numpy as np
import pandas as pd

from .assets import ASSETS, Asset
from .config import DEFAULT_SEED


def _asset_seed(asset_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{asset_id}:{seed}".encode()).hexdigest()
    return int(digest[:8], 16)


def _correlated_noise(rng: np.random.Generator, size: int, rho: float = 0.82) -> np.ndarray:
    innovations = rng.normal(0, 1, size)
    result = np.empty(size)
    result[0] = innovations[0]
    for index in range(1, size):
        result[index] = rho * result[index - 1] + np.sqrt(1 - rho**2) * innovations[index]
    return result


def _solar_power(
    capacity: float,
    timestamps: pd.DatetimeIndex,
    cloud_cover: np.ndarray,
    temperature: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    hour = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60
    day = timestamps.dayofyear.to_numpy()
    daylight = np.clip(np.sin(np.pi * (hour - 5.8) / 13.7), 0, None)
    seasonal = 0.84 + 0.16 * np.sin(2 * np.pi * (day - 80) / 365)
    irradiance = np.clip(1020 * daylight * seasonal * (1 - 0.68 * cloud_cover), 0, 1100)
    temperature_factor = np.clip(1 - 0.0038 * np.maximum(temperature - 25, 0), 0.82, 1.02)
    expected = capacity * irradiance / 1000 * temperature_factor * 0.975
    return expected, irradiance


def _wind_power(capacity: float, wind_speed: np.ndarray) -> np.ndarray:
    cut_in, rated, cut_out = 3.0, 12.5, 25.0
    ramp = np.clip((wind_speed**3 - cut_in**3) / (rated**3 - cut_in**3), 0, 1)
    return np.where((wind_speed >= cut_in) & (wind_speed <= cut_out), capacity * ramp, 0)


def _generate_asset(
    asset: Asset,
    timestamps: pd.DatetimeIndex,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(_asset_seed(asset["asset_id"], seed))
    size = len(timestamps)
    day = timestamps.dayofyear.to_numpy()
    hour = timestamps.hour.to_numpy()
    correlated = _correlated_noise(rng, size)
    cloud = np.clip(0.43 + 0.19 * correlated + 0.12 * np.sin(day / 7), 0.02, 0.98)
    temperature = (
        21
        + 7 * np.sin(2 * np.pi * (hour - 8) / 24)
        + 6 * np.sin(2 * np.pi * (day - 120) / 365)
        + rng.normal(0, 1.1, size)
    )
    availability = np.clip(asset["expected_availability"] + rng.normal(0, 0.006, size), 0.91, 1)
    wind_speed = np.clip(
        7.4 + 2.2 * correlated + 1.4 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 0.7, size),
        0,
        31,
    )
    if asset["technology"] == "solar":
        expected, irradiance = _solar_power(asset["capacity_mw"], timestamps, cloud, temperature)
    elif asset["technology"] == "wind":
        expected = _wind_power(asset["capacity_mw"], wind_speed)
        irradiance = np.zeros(size)
    else:
        price_signal = np.sin(2 * np.pi * (hour - 15) / 24)
        expected = asset["capacity_mw"] * 0.34 * price_signal
        irradiance = np.zeros(size)

    noise_scale = np.maximum(np.abs(expected) * 0.035, asset["capacity_mw"] * 0.006)
    actual = expected * availability + rng.normal(0, noise_scale, size)
    if asset["technology"] != "battery":
        actual = np.clip(actual, 0, asset["capacity_mw"] * 1.01)

    anomaly_type = np.full(size, "none", dtype=object)
    scenario_id = np.full(size, "", dtype=object)
    if asset["asset_id"] == "sol-ext-02":
        mask = timestamps >= timestamps[-1] - pd.DateOffset(days=7)
        degradation = np.linspace(0.04, 0.18, mask.sum())
        actual[mask] *= 1 - degradation
        anomaly_type[mask] = "soiling"
        scenario_id[mask] = "scenario_soiling_progressive"
    if asset["asset_id"] == "wnd-ara-03":
        start = timestamps[-1] - pd.DateOffset(days=3)
        mask = (timestamps >= start) & (timestamps < start + pd.DateOffset(hours=18))
        actual[mask] *= 0.58
        anomaly_type[mask] = "yaw_misalignment"
        scenario_id[mask] = "scenario_yaw_error"
    if asset["asset_id"] == "sol-cmn-01":
        start = timestamps[-1] - pd.DateOffset(days=11)
        mask = (timestamps >= start) & (timestamps < start + pd.DateOffset(hours=8))
        matching = np.flatnonzero(mask)
        if len(matching):
            temperature[mask] = temperature[matching[0]]
            anomaly_type[mask] = "frozen_sensor"
            scenario_id[mask] = "scenario_sensor_frozen"

    price = 57 + 18 * np.sin(2 * np.pi * (hour - 10) / 24) + 7 * correlated
    price = np.clip(price, -18, 145)
    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "asset_id": asset["asset_id"],
            "asset_name": asset["name"],
            "technology": asset["technology"],
            "region": asset["region"],
            "installed_capacity_mw": asset["capacity_mw"],
            "power_mw": actual.round(5),
            "expected_power_mw": expected.round(5),
            "energy_mwh": actual.round(5),
            "availability": availability.round(5),
            "irradiance_wm2": irradiance.round(3),
            "temperature_c": temperature.round(3),
            "cloud_cover_fraction": cloud.round(5),
            "wind_speed_ms": wind_speed.round(4),
            "price_eur_mwh": price.round(3),
            "curtailment_flag": False,
            "quality_flag": "valid",
            "is_synthetic": True,
            "scenario_id": scenario_id,
            "anomaly_type": anomaly_type,
            "source_id": "synthetic_scada",
        }
    )


def generate_scada(
    *,
    days: int = 90,
    frequency: str = "1h",
    end: str = "2026-07-28T00:00:00Z",
    seed: int = DEFAULT_SEED,
    assets: Iterable[Asset] = ASSETS,
) -> pd.DataFrame:
    """Generate a deterministic, UTC-aware SCADA dataset for the demo portfolio."""

    end_timestamp = pd.Timestamp(end)
    start_timestamp = end_timestamp - pd.DateOffset(days=days)
    timestamps = pd.date_range(
        start=start_timestamp,
        end=end_timestamp,
        freq=frequency,
        inclusive="right",
    )
    frames = [_generate_asset(asset, timestamps, seed) for asset in assets]
    result = pd.concat(frames, ignore_index=True)
    result["ingestion_run_id"] = f"demo-{seed}"
    return result.sort_values(["timestamp_utc", "asset_id"], ignore_index=True)
