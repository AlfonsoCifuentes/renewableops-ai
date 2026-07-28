from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_silver_quality_invariants() -> None:
    frame = pd.read_parquet(ROOT / "data/lakehouse/silver/generation.parquet")
    assert not frame.duplicated(["asset_id", "timestamp_utc"]).any()
    assert frame["timestamp_utc"].dt.tz is not None
    assert frame["availability"].between(0, 1).all()
    non_battery = frame["technology"] != "battery"
    assert (frame.loc[non_battery, "power_mw"] >= -0.001).all()
    assert (
        frame.loc[non_battery, "power_mw"] <= frame.loc[non_battery, "installed_capacity_mw"] * 1.03
    ).all()


def test_gold_quantiles_and_capacity_bounds() -> None:
    frame = pd.read_parquet(ROOT / "data/lakehouse/gold/forecast_evaluation.parquet")
    assert (frame["p10_mw"] <= frame["p50_mw"]).all()
    assert (frame["p50_mw"] <= frame["p90_mw"]).all()
    assert (frame["p90_mw"] <= frame["installed_capacity_mw"] + 1e-9).all()
