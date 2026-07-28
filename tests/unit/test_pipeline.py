from __future__ import annotations

from renewableops.pipeline import clean_silver
from renewableops.synthetic import generate_scada


def test_silver_deduplicates_business_key() -> None:
    frame = generate_scada(days=1)
    duplicate = frame.iloc[[0]]
    cleaned = clean_silver(frame._append(duplicate, ignore_index=True))
    assert len(cleaned) == len(frame)
    assert cleaned.groupby(["asset_id", "timestamp_utc"]).size().max() == 1
