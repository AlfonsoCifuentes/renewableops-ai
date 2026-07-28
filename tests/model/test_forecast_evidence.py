from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_each_technology_beats_persistence_with_recorded_intervals() -> None:
    metrics = json.loads((ROOT / "data/models/forecast_metrics.json").read_text(encoding="utf-8"))
    for technology in ("solar", "wind"):
        candidates = [row for row in metrics if row["technology"] == technology]
        champion = min(candidates, key=lambda row: row["mae_mw"])
        assert champion["skill_vs_persistence"] > 0
        assert 0 < champion["coverage_p10_p90"] <= 1
        assert champion["test_rows"] > 0
