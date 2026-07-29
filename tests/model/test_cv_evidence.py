from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cv_benchmark_records_untouched_test_and_full_metrics() -> None:
    metrics = json.loads((ROOT / "data/models/cv_metrics.json").read_text(encoding="utf-8"))
    assert metrics["test_used_for_selection"] is False
    assert metrics["champion"] in metrics["candidate_validation"]
    assert len(metrics["candidate_validation"]) >= 4
    assert 0 <= metrics["balanced_accuracy"] <= 1
    assert 0 <= metrics["macro_f1"] <= 1
    assert 0 <= metrics["pr_auc"] <= 1
    assert 0 <= metrics["roc_auc"] <= 1
    assert 0 <= metrics["brier_score"] <= 1
    assert metrics["confusion_matrix"]
    assert metrics["class_order"]


def test_elpv_evidence_is_attributed_when_extra_is_installed() -> None:
    metrics = json.loads((ROOT / "data/models/cv_metrics.json").read_text(encoding="utf-8"))
    if metrics["dataset"] == "ELPV":
        assert metrics["images"] == 2624
        assert metrics["license"].startswith("CC BY-NC-SA 4.0")
        assert metrics["annotation_hash"].startswith("sha256:")
        assert metrics["slices_by_cell_type"]["mono"]
        assert metrics["slices_by_cell_type"]["poly"]
