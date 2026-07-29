import json

import pytest
from renewableops.approvals import approve_model


def _write_registry(model_dir):
    registry = {
        "registry_version": "1.0.0",
        "aliases": {
            "solar": {
                "scope": "evaluation_only",
                "aliases": {
                    "Champion": "random_forest",
                    "Challenger": "extra_trees",
                },
                "champion_metrics": {"validation_mae_mw": 1.2},
                "gates": {"positive_skill_vs_persistence": True},
                "approval": {"status": "pending", "required": True},
            }
        },
    }
    (model_dir / "model_registry.json").write_text(
        json.dumps(registry),
        encoding="utf-8",
    )


def test_approval_is_bound_to_selected_artifact(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    _write_registry(model_dir)
    artifact = model_dir / "solar_forecast_champion.joblib"
    artifact.write_bytes(b"serialized-model")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "content_hash": "sha256:dataset",
                "schema_hash": "schema",
                "run_id": "run-1",
            }
        ),
        encoding="utf-8",
    )

    decision = approve_model(
        technology="solar",
        model="random_forest",
        approver="Portfolio Owner",
        rationale="Temporal metrics, artifact integrity and limitations were reviewed.",
        model_dir=model_dir,
        manifest_path=manifest,
        audit_path=tmp_path / "audit.jsonl",
    )

    registry = json.loads((model_dir / "model_registry.json").read_text(encoding="utf-8"))
    approval = registry["aliases"]["solar"]["approval"]
    assert approval["status"] == "approved"
    assert approval["artifact_sha256"] == decision["artifact"]["sha256"]
    assert approval["evidence_hash"] == decision["evidence_hash"]
    receipt = model_dir / "approvals" / approval["receipt"].split("/")[-1]
    assert receipt.exists()


def test_challenger_cannot_bypass_model_selection(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    _write_registry(model_dir)
    (model_dir / "solar_forecast_champion.joblib").write_bytes(b"serialized-model")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="not the selected Champion"):
        approve_model(
            technology="solar",
            model="extra_trees",
            approver="Portfolio Owner",
            rationale="This deliberately attempts to bypass the validated ranking.",
            model_dir=model_dir,
            manifest_path=manifest,
            audit_path=tmp_path / "audit.jsonl",
        )
