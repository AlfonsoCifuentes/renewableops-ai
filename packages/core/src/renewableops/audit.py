"""Tamper-evident local audit events for the portfolio demonstration."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    resource_version: str
    result: str
    correlation_id: str
    metadata: dict[str, Any]
    previous_hash: str
    event_hash: str


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def _hash_event(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def read_events(path: Path) -> list[AuditEvent]:
    """Read a JSONL chain; missing audit storage is an empty chain."""

    if not path.exists():
        return []
    events: list[AuditEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw: dict[str, Any] = json.loads(line)
            metadata = raw.get("metadata")
            events.append(
                AuditEvent(
                    event_id=str(raw["event_id"]),
                    timestamp=str(raw["timestamp"]),
                    actor=str(raw["actor"]),
                    action=str(raw["action"]),
                    resource=str(raw["resource"]),
                    resource_version=str(raw["resource_version"]),
                    result=str(raw["result"]),
                    correlation_id=str(raw["correlation_id"]),
                    metadata=dict(metadata) if isinstance(metadata, dict) else {},
                    previous_hash=str(raw["previous_hash"]),
                    event_hash=str(raw["event_hash"]),
                )
            )
    return events


def append_event(
    path: Path,
    *,
    actor: str,
    action: str,
    resource: str,
    resource_version: str,
    result: str,
    correlation_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append one canonical event linked to the previous event hash."""

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_events(path)
    previous_hash = existing[-1].event_hash if existing else "GENESIS"
    base = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "resource_version": resource_version,
        "result": result,
        "correlation_id": correlation_id,
        "metadata": metadata or {},
        "previous_hash": previous_hash,
    }
    event = AuditEvent(
        event_id=str(base["event_id"]),
        timestamp=str(base["timestamp"]),
        actor=actor,
        action=action,
        resource=resource,
        resource_version=resource_version,
        result=result,
        correlation_id=correlation_id,
        metadata=metadata or {},
        previous_hash=previous_hash,
        event_hash=_hash_event(base),
    )
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(asdict(event), sort_keys=True) + "\n")
    return event


def verify_chain(events: list[AuditEvent]) -> tuple[bool, int | None]:
    """Verify link and content hashes, returning the first invalid index."""

    expected_previous = "GENESIS"
    for index, event in enumerate(events):
        payload = asdict(event)
        event_hash = payload.pop("event_hash")
        if event.previous_hash != expected_previous or _hash_event(payload) != event_hash:
            return False, index
        expected_previous = event.event_hash
    return True, None
