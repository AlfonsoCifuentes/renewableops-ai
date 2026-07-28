import json
from dataclasses import asdict

from renewableops.audit import append_event, read_events, verify_chain


def test_audit_chain_detects_tampering(tmp_path):
    path = tmp_path / "audit.jsonl"
    append_event(
        path,
        actor="test",
        action="DATA_INGESTED",
        resource="bronze",
        resource_version="1",
        result="success",
        correlation_id="corr-1",
    )
    append_event(
        path,
        actor="test",
        action="SNAPSHOT_PUBLISHED",
        resource="snapshot",
        resource_version="1",
        result="success",
        correlation_id="corr-1",
    )
    valid, invalid_index = verify_chain(read_events(path))
    assert valid is True
    assert invalid_index is None

    payloads = [asdict(event) for event in read_events(path)]
    payloads[0]["result"] = "failed"
    path.write_text("\n".join(json.dumps(row) for row in payloads), encoding="utf-8")
    valid, invalid_index = verify_chain(read_events(path))
    assert valid is False
    assert invalid_index == 0
