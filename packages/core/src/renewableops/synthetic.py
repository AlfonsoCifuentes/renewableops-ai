"""Vectorized, deterministic SCADA generation with labelled failure scenarios."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .assets import ASSETS, Asset
from .config import DEFAULT_SEED

SCENARIO_NAMES = (
    "frozen_sensor",
    "sensor_drift",
    "missing_values",
    "duplicates",
    "late_timestamps",
    "out_of_range",
    "inverter_loss",
    "soiling",
    "curtailment",
    "overtemperature",
    "rotor_imbalance",
    "high_vibration",
    "yaw_error",
    "communication_loss",
    "malicious_tampering",
    "schema_change",
    "unit_change",
    "event_reordering",
    "late_backfill",
    "total_outage",
)

SCENARIO_METADATA: dict[str, tuple[str, str, str]] = {
    "frozen_sensor": ("frozen_sensor", "medium", "sensor_frozen_rule"),
    "sensor_drift": ("sensor_drift", "medium", "sensor_drift_monitor"),
    "missing_values": ("missing_values", "low", "completeness_contract"),
    "duplicates": ("duplicate_event", "low", "unique_key_contract"),
    "late_timestamps": ("late_timestamp", "medium", "event_time_watermark"),
    "out_of_range": ("out_of_range", "high", "physical_range_rule"),
    "inverter_loss": ("inverter_loss", "high", "solar_power_rule"),
    "soiling": ("soiling", "medium", "residual_plus_isolation_forest"),
    "curtailment": ("curtailment", "low", "curtailment_flag_rule"),
    "overtemperature": ("overtemperature", "high", "temperature_rule"),
    "rotor_imbalance": ("rotor_imbalance", "high", "rotor_vibration_rule"),
    "high_vibration": ("high_vibration", "high", "vibration_threshold"),
    "yaw_error": ("yaw_misalignment", "medium", "yaw_error_rule"),
    "communication_loss": ("communication_loss", "high", "freshness_monitor"),
    "malicious_tampering": ("simulated_tampering", "critical", "integrity_and_range_rules"),
    "schema_change": ("schema_change", "medium", "schema_fingerprint_monitor"),
    "unit_change": ("unit_change", "critical", "unit_contract"),
    "event_reordering": ("event_reordering", "low", "sequence_monitor"),
    "late_backfill": ("late_backfill", "low", "watermark_reconciliation"),
    "total_outage": ("total_outage", "critical", "availability_and_power_rule"),
}

SOLAR_SCENARIOS = {"inverter_loss", "soiling"}
WIND_SCENARIOS = {"rotor_imbalance", "high_vibration", "yaw_error"}


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
    interval_hours = (timestamps[1] - timestamps[0]).total_seconds() / 3600 if size > 1 else 1.0
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
    reactive_power = actual * (0.08 + 0.015 * correlated)
    module_temperature = temperature + irradiance * 0.028
    inverter_temperature = temperature + np.maximum(actual, 0) / max(asset["capacity_mw"], 1) * 21
    wind_direction = np.mod(225 + 34 * correlated, 360)
    rotor_speed = np.clip(wind_speed * 1.15, 0, 28)
    vibration = np.clip(0.85 + 0.11 * wind_speed + rng.normal(0, 0.08, size), 0, None)
    yaw_error = np.clip(rng.normal(0, 3.2, size), -18, 18)
    frame = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "ingested_at": timestamps + timedelta(minutes=5),
            "asset_id": asset["asset_id"],
            "asset_name": asset["name"],
            "technology": asset["technology"],
            "region": asset["region"],
            "installed_capacity_mw": asset["capacity_mw"],
            "power_mw": actual.round(5),
            "active_power_kw": (actual * 1000).round(2),
            "reactive_power_kvar": (reactive_power * 1000).round(2),
            "expected_power_mw": expected.round(5),
            "energy_mwh": (actual * interval_hours).round(6),
            "availability": availability.round(5),
            "irradiance_wm2": irradiance.round(3),
            "temperature_c": temperature.round(3),
            "ambient_temperature_c": temperature.round(3),
            "module_temperature_c": np.where(
                asset["technology"] == "solar",
                module_temperature,
                np.nan,
            ).round(3),
            "inverter_temperature_c": np.where(
                asset["technology"] == "solar",
                inverter_temperature,
                np.nan,
            ).round(3),
            "dc_voltage_v": np.where(
                asset["technology"] == "solar",
                760 + 24 * correlated,
                np.nan,
            ).round(2),
            "dc_current_a": np.where(
                asset["technology"] == "solar",
                np.maximum(actual, 0) * 1000 / 760,
                np.nan,
            ).round(2),
            "ac_voltage_v": np.where(
                asset["technology"] == "solar",
                400 + 2.1 * correlated,
                np.nan,
            ).round(2),
            "frequency_hz": (50 + rng.normal(0, 0.015, size)).round(4),
            "cloud_cover_fraction": cloud.round(5),
            "wind_speed_ms": wind_speed.round(4),
            "wind_direction_deg": wind_direction.round(2),
            "rotor_speed_rpm": np.where(
                asset["technology"] == "wind",
                rotor_speed,
                np.nan,
            ).round(3),
            "generator_speed_rpm": np.where(
                asset["technology"] == "wind",
                rotor_speed * 82,
                np.nan,
            ).round(2),
            "nacelle_temperature_c": np.where(
                asset["technology"] == "wind",
                temperature + 7 + np.maximum(actual, 0) / max(asset["capacity_mw"], 1) * 9,
                np.nan,
            ).round(3),
            "gearbox_temperature_c": np.where(
                asset["technology"] == "wind",
                temperature + 18 + np.maximum(actual, 0) / max(asset["capacity_mw"], 1) * 16,
                np.nan,
            ).round(3),
            "bearing_temperature_c": np.where(
                asset["technology"] == "wind",
                temperature + 12 + vibration * 2,
                np.nan,
            ).round(3),
            "vibration_rms": np.where(
                asset["technology"] == "wind",
                vibration,
                np.nan,
            ).round(4),
            "pitch_angle_deg": np.where(
                asset["technology"] == "wind",
                np.clip((wind_speed - 11) * 2.4, 0, 28),
                np.nan,
            ).round(3),
            "yaw_error_deg": np.where(
                asset["technology"] == "wind",
                yaw_error,
                np.nan,
            ).round(3),
            "price_eur_mwh": price.round(3),
            "curtailment_flag": False,
            "curtailment_mw": 0.0,
            "alarm_code": "",
            "soiling_index": np.where(
                asset["technology"] == "solar",
                1.0,
                np.nan,
            ),
            "quality_flag": "valid",
            "is_synthetic": True,
            "scenario_id": scenario_id,
            "anomaly_type": anomaly_type,
            "anomaly_start": "",
            "anomaly_end": "",
            "severity": "none",
            "injected_by": "",
            "expected_detection": "",
            "schema_version": "1.0",
            "measurement_unit": "MW",
            "event_sequence": np.arange(size, dtype=np.int64),
            "source_id": "synthetic_scada",
        }
    )
    defaults = frame["anomaly_type"].ne("none")
    if defaults.any():
        frame.loc[defaults, "severity"] = "medium"
        frame.loc[defaults, "injected_by"] = "deterministic_demo_profile"
        frame.loc[defaults, "expected_detection"] = "layered_anomaly_detector"
        for scenario in frame.loc[defaults, "scenario_id"].unique():
            mask = frame["scenario_id"].eq(scenario)
            frame.loc[mask, "anomaly_start"] = frame.loc[mask, "timestamp_utc"].min().isoformat()
            frame.loc[mask, "anomaly_end"] = frame.loc[mask, "timestamp_utc"].max().isoformat()
    return frame


def _eligible_assets(frame: pd.DataFrame, scenario: str) -> list[str]:
    candidates = frame[["asset_id", "technology"]].drop_duplicates()
    if scenario in SOLAR_SCENARIOS:
        candidates = candidates.loc[candidates["technology"] == "solar"]
    elif scenario in WIND_SCENARIOS:
        candidates = candidates.loc[candidates["technology"] == "wind"]
    return sorted(candidates["asset_id"].astype(str).tolist())


def inject_failure_scenarios(
    frame: pd.DataFrame,
    scenarios: Iterable[str] = SCENARIO_NAMES,
) -> pd.DataFrame:
    """Inject configurable, labelled failures without hiding raw effects."""

    result = frame.copy()
    result["timestamp_utc"] = pd.to_datetime(result["timestamp_utc"], utc=True)
    latest = result["timestamp_utc"].max()
    duplicate_rows: list[pd.DataFrame] = []
    for index, scenario in enumerate(scenarios):
        if scenario not in SCENARIO_METADATA:
            raise ValueError(f"Unknown synthetic scenario: {scenario}")
        candidates = _eligible_assets(result, scenario)
        if not candidates:
            continue
        asset_id = candidates[index % len(candidates)]
        start = latest - timedelta(hours=18 + index * 7)
        end = start + timedelta(hours=4)
        mask = (
            result["asset_id"].eq(asset_id)
            & result["timestamp_utc"].ge(start)
            & result["timestamp_utc"].lt(end)
        )
        positions = result.index[mask]
        if positions.empty:
            continue
        anomaly_type, severity, expected_detection = SCENARIO_METADATA[scenario]
        create_duplicate = False

        if scenario == "frozen_sensor":
            result.loc[mask, "temperature_c"] = result.loc[positions[0], "temperature_c"]
        elif scenario == "sensor_drift":
            result.loc[mask, "temperature_c"] += np.linspace(0, 14, len(positions))
        elif scenario == "missing_values":
            result.loc[mask, ["power_mw", "active_power_kw"]] = np.nan
        elif scenario == "duplicates":
            create_duplicate = True
        elif scenario == "late_timestamps":
            result.loc[mask, "timestamp_utc"] += timedelta(minutes=17)
        elif scenario == "out_of_range":
            result.loc[mask, "temperature_c"] = 165.0
            result.loc[mask, "availability"] = 1.2
        elif scenario == "inverter_loss":
            result.loc[mask, ["power_mw", "active_power_kw", "energy_mwh"]] *= 0.56
            result.loc[mask, "alarm_code"] = "INV_PARTIAL_LOSS"
        elif scenario == "soiling":
            degradation = np.linspace(0.04, 0.22, len(positions))
            for column in ("power_mw", "active_power_kw", "energy_mwh"):
                result.loc[mask, column] *= 1 - degradation
            result.loc[mask, "soiling_index"] = 1 - degradation
        elif scenario == "curtailment":
            curtailed = result.loc[mask, "power_mw"] * 0.35
            result.loc[mask, "curtailment_flag"] = True
            result.loc[mask, "curtailment_mw"] = curtailed
            result.loc[mask, "power_mw"] -= curtailed
        elif scenario == "overtemperature":
            for column in (
                "inverter_temperature_c",
                "nacelle_temperature_c",
                "gearbox_temperature_c",
            ):
                result.loc[mask, column] = result.loc[mask, column].fillna(70) + 35
        elif scenario == "rotor_imbalance":
            result.loc[mask, "vibration_rms"] *= 2.8
            result.loc[mask, "rotor_speed_rpm"] *= 0.72
        elif scenario == "high_vibration":
            result.loc[mask, "vibration_rms"] = 8.5
        elif scenario == "yaw_error":
            result.loc[mask, "yaw_error_deg"] = 24.0
            result.loc[mask, ["power_mw", "active_power_kw", "energy_mwh"]] *= 0.68
        elif scenario == "communication_loss":
            result.loc[
                mask,
                ["power_mw", "active_power_kw", "availability", "frequency_hz"],
            ] = np.nan
        elif scenario == "malicious_tampering":
            result.loc[mask, "power_mw"] = result.loc[mask, "installed_capacity_mw"] * 1.35
            result.loc[mask, "alarm_code"] = "SIMULATED_INTEGRITY_VIOLATION"
        elif scenario == "schema_change":
            result.loc[mask, "schema_version"] = "2.0-unexpected"
        elif scenario == "unit_change":
            result.loc[mask, "power_mw"] *= 1000
            result.loc[mask, "measurement_unit"] = "kW_mislabeled_as_MW"
        elif scenario == "event_reordering":
            result.loc[mask, "event_sequence"] = result.loc[mask, "event_sequence"].to_numpy()[::-1]
        elif scenario == "late_backfill":
            result.loc[mask, "ingested_at"] = result.loc[mask, "timestamp_utc"] + timedelta(days=3)
        elif scenario == "total_outage":
            result.loc[mask, ["power_mw", "active_power_kw", "energy_mwh"]] = 0.0
            result.loc[mask, "availability"] = 0.0
            result.loc[mask, "alarm_code"] = "ASSET_TRIP"

        result.loc[mask, "scenario_id"] = f"scenario_{scenario}"
        result.loc[mask, "anomaly_type"] = anomaly_type
        result.loc[mask, "anomaly_start"] = result.loc[mask, "timestamp_utc"].min().isoformat()
        result.loc[mask, "anomaly_end"] = result.loc[mask, "timestamp_utc"].max().isoformat()
        result.loc[mask, "severity"] = severity
        result.loc[mask, "injected_by"] = "renewableops.synthetic.inject_failure_scenarios"
        result.loc[mask, "expected_detection"] = expected_detection
        if create_duplicate:
            duplicates = result.loc[mask].copy()
            duplicates["quality_flag"] = "duplicate"
            duplicate_rows.append(duplicates)

    if duplicate_rows:
        result = pd.concat([result, *duplicate_rows], ignore_index=True)
    return result.sort_values(["timestamp_utc", "asset_id", "event_sequence"], ignore_index=True)


def generate_scada(
    *,
    days: int = 90,
    frequency: str = "1h",
    end: str = "2026-07-28T00:00:00Z",
    seed: int = DEFAULT_SEED,
    assets: Iterable[Asset] = ASSETS,
    scenarios: Iterable[str] | None = None,
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
    if scenarios is not None:
        result = inject_failure_scenarios(result, scenarios)
    return result.sort_values(["timestamp_utc", "asset_id"], ignore_index=True)


def write_scada_profile(
    output_dir: Path,
    *,
    days: int = 730,
    frequency: str = "5min",
    end: str = "2026-07-28T00:00:00Z",
    seed: int = DEFAULT_SEED,
    assets: Iterable[Asset] = ASSETS,
) -> dict[str, Any]:
    """Write a bounded-memory, partitioned high-frequency SCADA profile."""

    asset_list = list(assets)
    assignments: dict[str, list[str]] = {asset["asset_id"]: [] for asset in asset_list}
    for index, scenario in enumerate(SCENARIO_NAMES):
        eligible = [
            asset
            for asset in asset_list
            if (scenario not in SOLAR_SCENARIOS or asset["technology"] == "solar")
            and (scenario not in WIND_SCENARIOS or asset["technology"] == "wind")
        ]
        selected = eligible[index % len(eligible)]
        assignments[selected["asset_id"]].append(scenario)

    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    rows = 0
    scenarios_found: set[str] = set()
    min_timestamp: str | None = None
    max_timestamp: str | None = None
    schema: dict[str, str] = {}
    for asset in asset_list:
        partition = generate_scada(
            days=days,
            frequency=frequency,
            end=end,
            seed=seed,
            assets=[asset],
            scenarios=assignments[asset["asset_id"]],
        )
        path = output_dir / f"asset_id={asset['asset_id']}.parquet"
        partition.to_parquet(path, index=False, compression="zstd")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files[path.name] = f"sha256:{digest}"
        rows += len(partition)
        for value in partition["scenario_id"].unique():
            normalized = value.removeprefix("scenario_")
            if normalized in SCENARIO_NAMES:
                scenarios_found.add(normalized)
        partition_min = pd.Timestamp(partition["timestamp_utc"].min()).isoformat()
        partition_max = pd.Timestamp(partition["timestamp_utc"].max()).isoformat()
        min_timestamp = min(filter(None, [min_timestamp, partition_min]), default=partition_min)
        max_timestamp = max(filter(None, [max_timestamp, partition_max]), default=partition_max)
        if not schema:
            schema = {column: str(dtype) for column, dtype in partition.dtypes.items()}

    manifest = {
        "profile": "scada_5min_two_year",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "is_synthetic": True,
        "days": days,
        "frequency": frequency,
        "assets": len(asset_list),
        "rows": rows,
        "min_timestamp": min_timestamp,
        "max_timestamp": max_timestamp,
        "scenarios": sorted(scenarios_found),
        "scenario_count": len(scenarios_found),
        "schema_hash": (
            f"sha256:{hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()}"
        ),
        "files": files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest
