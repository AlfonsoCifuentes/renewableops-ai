import json

from renewableops.modeling import ModelMetrics
from renewableops.registry import write_registry


def _metric(technology: str, model: str, mae: float) -> ModelMetrics:
    return ModelMetrics(
        technology=technology,
        model=model,
        mae_mw=mae,
        rmse_mw=mae * 1.2,
        nmae=0.04,
        bias_mw=0.01,
        skill_vs_persistence=0.5,
        coverage_p10_p90=0.8,
        dataset_rows=100,
        test_rows=20,
    )


def test_registry_has_reviewable_aliases(tmp_path):
    metrics = [
        _metric("solar", "extra_trees", 1.0),
        _metric("solar", "ridge", 2.0),
        _metric("wind", "extra_trees", 2.0),
        _metric("wind", "ridge", 3.0),
    ]
    path = write_registry(metrics, model_dir=tmp_path, dataset_manifest="manifest.json")
    registry = json.loads(path.read_text(encoding="utf-8"))
    assert registry["aliases"]["solar"]["aliases"]["Champion"] == "extra_trees"
    assert registry["automatic_production_promotion"] is False
