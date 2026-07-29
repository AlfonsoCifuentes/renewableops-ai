from __future__ import annotations

import numpy as np
import pandas as pd
from renewableops.assets import ASSETS
from renewableops.synthetic import SCENARIO_NAMES, generate_scada, write_scada_profile


def test_scada_is_deterministic_and_utc() -> None:
    first = generate_scada(days=2)
    second = generate_scada(days=2)
    pd.testing.assert_frame_equal(first, second)
    assert str(first["timestamp_utc"].dtype) == "datetime64[ns, UTC]"
    assert first["is_synthetic"].all()
    assert first.groupby(["asset_id", "timestamp_utc"]).size().max() == 1


def test_scada_respects_physical_capacity() -> None:
    frame = generate_scada(days=4)
    renewables = frame.loc[frame["technology"].isin(["solar", "wind"])]
    assert (renewables["power_mw"] >= 0).all()
    assert (renewables["power_mw"] <= renewables["installed_capacity_mw"] * 1.03).all()
    assert frame["availability"].between(0, 1).all()


def test_five_minute_profile_integrates_energy_over_interval() -> None:
    frame = generate_scada(days=1, frequency="5min", assets=[ASSETS[0]])
    np.testing.assert_allclose(
        frame["energy_mwh"].to_numpy(),
        (frame["power_mw"] / 12).to_numpy(),
        rtol=0,
        atol=1.1e-6,
    )
    assert len(frame) == 288


def test_all_failure_scenarios_are_configurable_and_labelled() -> None:
    frame = generate_scada(days=8, scenarios=SCENARIO_NAMES)
    injected = {
        value.removeprefix("scenario_")
        for value in frame["scenario_id"].unique()
        if value.startswith("scenario_")
    }
    assert set(SCENARIO_NAMES) <= injected
    labelled = frame["scenario_id"].isin([f"scenario_{name}" for name in SCENARIO_NAMES])
    assert frame.loc[labelled, "severity"].ne("none").all()
    assert frame.loc[labelled, "expected_detection"].ne("").all()
    assert frame.loc[labelled, "is_synthetic"].all()


def test_partitioned_profile_writer_is_bounded_and_complete(tmp_path) -> None:
    manifest = write_scada_profile(tmp_path / "scale", days=8, frequency="1h")
    assert manifest["assets"] == 12
    assert manifest["scenario_count"] == 20
    assert set(manifest["scenarios"]) == set(SCENARIO_NAMES)
    assert len(manifest["files"]) == 12
    assert all((tmp_path / "scale" / filename).exists() for filename in manifest["files"])
