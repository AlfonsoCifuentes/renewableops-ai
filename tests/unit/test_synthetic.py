from __future__ import annotations

import pandas as pd
from renewableops.synthetic import generate_scada


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
