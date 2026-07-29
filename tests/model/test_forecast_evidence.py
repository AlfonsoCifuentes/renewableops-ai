from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_each_technology_beats_persistence_with_recorded_intervals() -> None:
    metrics = json.loads((ROOT / "data/models/forecast_metrics.json").read_text(encoding="utf-8"))
    for technology in ("solar", "wind"):
        candidates = [row for row in metrics if row["technology"] == technology]
        champion = min(candidates, key=lambda row: row["validation_mae_mw"])
        assert champion["skill_vs_persistence"] > 0
        assert 0 < champion["coverage_p10_p90"] <= 1
        assert champion["test_rows"] > 0
        assert champion["validation_folds"] == 3
        assert champion["validation_gap_hours"] == 24
        assert champion["quantile_crossing_rate"] == 0


def test_forecast_selection_does_not_touch_test_and_covers_mandatory_baselines() -> None:
    for technology in ("solar", "wind"):
        evidence = json.loads(
            (ROOT / f"data/models/{technology}_forecast_evidence.json").read_text(
                encoding="utf-8"
            )
        )
        assert evidence["test_used_for_selection"] is False
        assert evidence["validation"]["method"] == "TimeSeriesSplit"
        assert evidence["validation"]["gap_hours"] == 24
        assert set(evidence["baselines"]) == {
            "persistence_1h",
            "same_hour_24h",
            "same_hour_168h",
            "hour_weekday_mean",
            "physical_expected_power",
        }
        assert evidence["quantiles"]["alphas"] == [0.1, 0.5, 0.9]
        buckets = evidence["horizon_metrics"]["buckets"]
        assert [bucket["label"] for bucket in buckets] == [
            "0–6 h",
            "7–12 h",
            "13–18 h",
            "19–24 h",
            "25–36 h",
            "37–48 h",
        ]
        assert all(bucket["observations"] > 0 for bucket in buckets)
        assert all(bucket["mae_mw"] >= 0 for bucket in buckets)


def test_solar_future_forecast_covers_both_days_without_midnight_collapse() -> None:
    forecasts = json.loads(
        (
            ROOT / "apps/dashboard/public/data/latest/forecasts.json"
        ).read_text(encoding="utf-8")
    )
    solar_day_two = [
        row
        for row in forecasts
        if row["technology"] == "solar" and 25 <= row["horizon_hours"] <= 48
    ]
    assert solar_day_two
    assert sum(row["p50_mw"] for row in solar_day_two) > 0
    assert all(0 <= row["p10_mw"] <= row["p50_mw"] <= row["p90_mw"] for row in solar_day_two)
