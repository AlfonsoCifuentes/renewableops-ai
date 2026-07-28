"""Validate the bounded, importable n8n workflow definitions."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    workflow_paths = sorted((ROOT / "workflows/n8n").glob("*.json"))
    names: set[str] = set()
    versions: set[str] = set()
    errors: list[str] = []
    for path in workflow_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        name = payload.get("name")
        version = payload.get("versionId")
        if not isinstance(name, str) or not name:
            errors.append(f"{path.name}: missing name")
        elif name in names:
            errors.append(f"{path.name}: duplicate name {name!r}")
        else:
            names.add(name)
        if not isinstance(version, str) or not version:
            errors.append(f"{path.name}: missing versionId")
        elif version in versions:
            errors.append(f"{path.name}: duplicate versionId")
        else:
            versions.add(version)
        node_names = {
            node.get("name") for node in payload.get("nodes", []) if isinstance(node, dict)
        }
        if not node_names:
            errors.append(f"{path.name}: no nodes")
        connections = payload.get("connections")
        if not isinstance(connections, dict):
            errors.append(f"{path.name}: invalid connections")
        elif not set(connections).issubset(node_names):
            errors.append(f"{path.name}: connection references unknown source node")
        if payload.get("active") is not False:
            errors.append(f"{path.name}: schedules must ship paused")
        if payload.get("settings", {}).get("timezone") != "Europe/Madrid":
            errors.append(f"{path.name}: timezone must be Europe/Madrid")
    if len(workflow_paths) != 6:
        errors.append(f"expected 6 workflows, found {len(workflow_paths)}")
    result = {
        "status": "passed" if not errors else "failed",
        "workflows": len(workflow_paths),
        "names": sorted(names),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
