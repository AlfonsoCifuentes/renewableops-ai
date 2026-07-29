"""Persistent Bronze ingestion for bounded official-source evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import DATA_DIR, MANIFEST_DIR
from .sources import (
    SourceError,
    SourcePayload,
    fetch_aemet,
    fetch_eurostat,
    fetch_pvgis,
    fetch_redata,
)

SOURCE_STATUS_PATH = MANIFEST_DIR / "source_status.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _commit() -> str:
    configured = os.getenv("GITHUB_SHA")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=DATA_DIR.parent,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _registry() -> dict[str, dict[str, Any]]:
    path = DATA_DIR / "source_registry.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = payload.get("sources", []) if isinstance(payload, dict) else []
    return {
        str(item["source_id"]): item
        for item in sources
        if isinstance(item, dict) and "source_id" in item
    }


def _record_count(source: SourcePayload) -> int:
    payload = source.payload
    if source.source_id == "eurostat_renewables":
        values = payload.get("value")
        return len(values) if isinstance(values, dict) else 0
    outputs = payload.get("outputs")
    if isinstance(outputs, dict):
        monthly = outputs.get("monthly")
        if isinstance(monthly, list):
            return len(monthly)
    included = payload.get("included")
    if isinstance(included, list):
        return sum(
            len(item.get("attributes", {}).get("values", []))
            for item in included
            if isinstance(item, dict) and isinstance(item.get("attributes"), dict)
        )
    records = payload.get("records")
    return len(records) if isinstance(records, list) else 1


def _persist(
    source: SourcePayload,
    *,
    run_id: str,
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metadata = registry[source.source_id]
    extraction_date = source.extracted_at[:10]
    relative_path = (
        Path("data")
        / "lakehouse"
        / "bronze"
        / "official"
        / source.source_id
        / f"extraction_date={extraction_date}"
        / f"run_id={run_id}"
        / "payload.json"
    )
    artifact_path = DATA_DIR.parent / relative_path
    envelope = {
        "source_id": source.source_id,
        "requested_url": source.requested_url,
        "status_code": source.status_code,
        "extracted_at": source.extracted_at,
        "source_updated_at": source.source_updated_at,
        "payload_checksum_sha256": source.checksum_sha256,
        "schema_fingerprint_sha256": source.schema_fingerprint_sha256,
        "request_id": source.request_id,
        "run_id": run_id,
        "response_headers": source.response_headers,
        "attribution": metadata["attribution"],
        "license_notes": metadata["license_notes"],
        "payload": source.payload,
    }
    _write_json(artifact_path, envelope)
    record_count = _record_count(source)
    manifest = {
        "dataset_id": f"{source.source_id}_bronze",
        "dataset_version": source.extracted_at,
        "run_id": run_id,
        "source_ids": [source.source_id],
        "row_count": record_count,
        "source_updated_at": source.source_updated_at,
        "schema_hash": f"sha256:{source.schema_fingerprint_sha256}",
        "payload_hash": f"sha256:{source.checksum_sha256}",
        "content_hash": f"sha256:{_sha256(artifact_path)}",
        "code_commit": _commit(),
        "quality_status": "passed",
        "artifact": relative_path.as_posix(),
        "attribution": metadata["attribution"],
        "license_notes": metadata["license_notes"],
    }
    manifest_path = MANIFEST_DIR / f"official_{source.source_id}.json"
    _write_json(manifest_path, manifest)
    return {
        "status": "success",
        "authority": metadata["authority"],
        "name": metadata["name"],
        "extracted_at": source.extracted_at,
        "source_updated_at": source.source_updated_at,
        "checksum_sha256": source.checksum_sha256,
        "schema_fingerprint_sha256": source.schema_fingerprint_sha256,
        "records": record_count,
        "artifact": relative_path.as_posix(),
        "manifest": manifest_path.relative_to(DATA_DIR.parent).as_posix(),
        "attribution": metadata["attribution"],
        "license_notes": metadata["license_notes"],
    }


def _safe_failure(error: Exception) -> str:
    if isinstance(error, SourceError):
        return str(error)
    return f"{type(error).__name__}: source request did not complete"


def ingest_official_sources() -> dict[str, Any]:
    """Fetch and persist three keyless official sources, plus AEMET when configured."""

    registry = _registry()
    generated_at = datetime.now(UTC)
    run_id = f"ingest-{generated_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    fetchers: tuple[tuple[str, Callable[[], SourcePayload]], ...] = (
        ("ree_redata", fetch_redata),
        ("pvgis", fetch_pvgis),
        ("eurostat_renewables", fetch_eurostat),
    )
    results: dict[str, dict[str, Any]] = {}
    for source_id, fetcher in fetchers:
        try:
            results[source_id] = _persist(
                fetcher(),
                run_id=run_id,
                registry=registry,
            )
        except Exception as error:  # noqa: BLE001 - failures are isolated by source
            metadata = registry[source_id]
            results[source_id] = {
                "status": "failed",
                "authority": metadata["authority"],
                "name": metadata["name"],
                "reason": _safe_failure(error),
                "fallback_source": metadata["fallback_source"],
            }

    aemet_metadata = registry["aemet"]
    if os.getenv("AEMET_API_KEY"):
        try:
            results["aemet"] = _persist(
                fetch_aemet(),
                run_id=run_id,
                registry=registry,
            )
        except Exception as error:  # noqa: BLE001 - optional source remains isolated
            results["aemet"] = {
                "status": "failed",
                "authority": aemet_metadata["authority"],
                "name": aemet_metadata["name"],
                "reason": _safe_failure(error),
                "fallback_source": aemet_metadata["fallback_source"],
            }
    else:
        results["aemet"] = {
            "status": "not_configured",
            "authority": aemet_metadata["authority"],
            "name": aemet_metadata["name"],
            "reason": "AEMET_API_KEY is not configured; this source is not used as evidence.",
            "fallback_source": aemet_metadata["fallback_source"],
        }

    required = [results[source_id]["status"] == "success" for source_id, _ in fetchers]
    report = {
        "run_id": run_id,
        "generated_at": generated_at.isoformat(),
        "status": "passed" if all(required) else "partial",
        "required_successes": sum(required),
        "required_sources": len(required),
        "sources": results,
    }
    _write_json(SOURCE_STATUS_PATH, report)
    return report


def load_source_status() -> dict[str, Any]:
    """Read the last bounded ingestion report without implying live freshness."""

    if not SOURCE_STATUS_PATH.exists():
        return {
            "status": "not_run",
            "required_successes": 0,
            "required_sources": 3,
            "sources": {},
        }
    payload: object = json.loads(SOURCE_STATUS_PATH.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"status": "invalid", "sources": {}}
