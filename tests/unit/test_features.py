from __future__ import annotations

from renewableops.features import build_features
from renewableops.synthetic import generate_scada


def test_lags_do_not_read_current_target() -> None:
    frame = generate_scada(days=3)
    featured = build_features(frame)
    asset = featured.loc[featured["asset_id"] == "sol-cmn-01"].reset_index(drop=True)
    assert asset.loc[24, "lag_24h_mw"] == asset.loc[0, "power_mw"]
    original_rolling = asset.loc[30, "rolling_24h_mw"]
    mutated = frame.copy()
    row_index = mutated.index[
        (mutated["asset_id"] == "sol-cmn-01")
        & (mutated["timestamp_utc"] == asset.loc[30, "timestamp_utc"])
    ][0]
    mutated.loc[row_index, "power_mw"] += 999
    rebuilt = build_features(mutated)
    rebuilt_asset = rebuilt.loc[rebuilt["asset_id"] == "sol-cmn-01"].reset_index(drop=True)
    assert rebuilt_asset.loc[30, "rolling_24h_mw"] == original_rolling
