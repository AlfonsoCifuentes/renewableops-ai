from __future__ import annotations

import json
from pathlib import Path

from renewableops import ingestion
from renewableops.sources import SourcePayload


def _payload(source_id: str) -> SourcePayload:
    return SourcePayload(
        source_id=source_id,
        requested_url=f"https://official.test/{source_id}?window=bounded",
        extracted_at="2026-07-29T06:00:00+00:00",
        source_updated_at="2026-07-28T23:00:00+00:00",
        status_code=200,
        checksum_sha256="a" * 64,
        schema_fingerprint_sha256="b" * 64,
        request_id=f"request-{source_id}",
        response_headers={"content-type": "application/json"},
        payload=(
            {
                "class": "dataset",
                "source": "ESTAT",
                "value": {"0": 24.9},
            }
            if source_id == "eurostat_renewables"
            else {"records": [{"value": 1}]}
        ),
    )


def test_official_ingestion_persists_bronze_and_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingestion, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(ingestion, "MANIFEST_DIR", tmp_path / "data" / "manifests")
    monkeypatch.setattr(
        ingestion,
        "SOURCE_STATUS_PATH",
        tmp_path / "data" / "manifests" / "source_status.json",
    )
    registry_path = tmp_path / "data" / "source_registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        "sources:\n"
        + "".join(
            (
                f"  - source_id: {source_id}\n"
                f"    name: {source_id}\n"
                "    authority: Test authority\n"
                "    attribution: Test attribution\n"
                "    license_notes: Test license\n"
                "    fallback_source: last_valid\n"
            )
            for source_id in ("ree_redata", "pvgis", "eurostat_renewables", "aemet")
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ingestion, "fetch_redata", lambda: _payload("ree_redata"))
    monkeypatch.setattr(ingestion, "fetch_pvgis", lambda: _payload("pvgis"))
    monkeypatch.setattr(
        ingestion,
        "fetch_eurostat",
        lambda: _payload("eurostat_renewables"),
    )
    monkeypatch.delenv("AEMET_API_KEY", raising=False)

    result = ingestion.ingest_official_sources()

    assert result["status"] == "passed"
    assert result["required_successes"] == 3
    status = json.loads(ingestion.SOURCE_STATUS_PATH.read_text(encoding="utf-8"))
    assert status["sources"]["aemet"]["status"] == "not_configured"
    for source_id in ("ree_redata", "pvgis", "eurostat_renewables"):
        evidence = status["sources"][source_id]
        artifact = tmp_path / evidence["artifact"]
        assert artifact.exists()
        envelope = json.loads(artifact.read_text(encoding="utf-8"))
        assert envelope["source_id"] == source_id
        assert envelope["payload_checksum_sha256"] == "a" * 64
