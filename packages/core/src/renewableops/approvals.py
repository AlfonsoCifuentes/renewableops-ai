"""Explicit, artifact-bound human approval for forecast champions."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .audit import append_event
from .config import DATA_DIR, MANIFEST_DIR, MODEL_DIR


def _load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required approval input is missing: {path.name}")
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def approve_model(
    *,
    technology: str,
    model: str,
    approver: str,
    rationale: str,
    model_dir: Path = MODEL_DIR,
    manifest_path: Path = MANIFEST_DIR / "generation_silver.json",
    audit_path: Path = DATA_DIR / "audit" / "events.jsonl",
) -> dict[str, Any]:
    """Approve only the selected, materialized champion and bind the decision to its hash."""

    if technology not in {"solar", "wind"}:
        raise ValueError("technology must be 'solar' or 'wind'")
    if len(approver.strip()) < 3:
        raise ValueError("approver must identify the human reviewer")
    if len(rationale.strip()) < 20:
        raise ValueError("rationale must explain the reviewed evidence")

    registry_path = model_dir / "model_registry.json"
    registry = _load_object(registry_path)
    raw_aliases = registry.get("aliases")
    aliases = raw_aliases if isinstance(raw_aliases, dict) else {}
    raw_record = aliases.get(technology)
    if not isinstance(raw_record, dict):
        raise ValueError(f"registry has no {technology} model")
    record = raw_record
    raw_model_aliases = record.get("aliases")
    model_aliases = raw_model_aliases if isinstance(raw_model_aliases, dict) else {}
    selected_model = str(model_aliases.get("Champion", ""))
    if model != selected_model:
        challenger = model_aliases.get("Challenger")
        suffix = (
            " It is the evaluated challenger and has no deployable artifact."
            if model == challenger
            else ""
        )
        raise ValueError(
            f"{technology}/{model} is not the selected Champion ({selected_model}).{suffix}"
        )

    artifact_path = model_dir / f"{technology}_forecast_champion.joblib"
    if not artifact_path.exists():
        raise FileNotFoundError(f"Deployable artifact is missing: {artifact_path.name}")
    manifest = _load_object(manifest_path)
    artifact_hash = f"sha256:{_hash_file(artifact_path)}"
    reviewed_at = datetime.now(UTC).isoformat()
    decision: dict[str, Any] = {
        "schema_version": "1.0.0",
        "decision": "approve",
        "scope": "portfolio_demo_inference",
        "technology": technology,
        "model": model,
        "alias": "Champion",
        "approver": approver.strip(),
        "rationale": rationale.strip(),
        "reviewed_at": reviewed_at,
        "dataset": {
            "manifest": "data/manifests/generation_silver.json",
            "content_hash": manifest.get("content_hash"),
            "schema_hash": manifest.get("schema_hash"),
            "run_id": manifest.get("run_id"),
        },
        "artifact": {
            "file": f"data/models/{artifact_path.name}",
            "sha256": artifact_hash,
            "size_bytes": artifact_path.stat().st_size,
        },
        "metrics": record.get("champion_metrics"),
        "gates": record.get("gates"),
        "limitations": [
            "Synthetic SCADA portfolio; not validated on a real operating plant.",
            "Approval covers portfolio demonstration inference, not autonomous control.",
            "A new artifact hash or training run requires a new human approval.",
        ],
    }
    evidence_hash = f"sha256:{_canonical_hash(decision)}"
    decision["evidence_hash"] = evidence_hash

    approvals_dir = model_dir / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    receipt_name = f"{technology}-{model}-{reviewed_at[:10]}.json"
    receipt_path = approvals_dir / receipt_name
    receipt_path.write_text(
        json.dumps(decision, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    record["scope"] = "portfolio_demo_inference"
    record["promotion_status"] = "approved"
    record["deployment_status"] = "approved_for_demo_inference"
    record["approval"] = {
        "status": "approved",
        "required": True,
        "approver": approver.strip(),
        "reviewed_at": reviewed_at,
        "rationale": rationale.strip(),
        "artifact_sha256": artifact_hash,
        "evidence_hash": evidence_hash,
        "receipt": f"data/models/approvals/{receipt_name}",
        "template": "governance/approvals/model-promotion-template.md",
    }
    registry["aliases"] = aliases
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    correlation_id = f"approval-{uuid.uuid4()}"
    append_event(
        audit_path,
        actor=approver.strip(),
        action="MODEL_APPROVED",
        resource=f"{technology}_forecast/{model}",
        resource_version=artifact_hash,
        result="success",
        correlation_id=correlation_id,
        metadata={
            "scope": "portfolio_demo_inference",
            "evidence_hash": evidence_hash,
            "receipt": f"data/models/approvals/{receipt_name}",
        },
    )
    return decision
