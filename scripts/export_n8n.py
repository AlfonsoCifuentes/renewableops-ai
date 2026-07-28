"""Validate that every committed n8n workflow is importable JSON."""

from __future__ import annotations

import json
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    workflows = sorted((root / "workflows" / "n8n").glob("*.json"))
    for workflow in workflows:
        payload = json.loads(workflow.read_text(encoding="utf-8"))
        required = {"name", "nodes", "connections"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"{workflow.name}: missing {sorted(missing)}")
        print(f"valid {workflow.name}: {len(payload['nodes'])} nodes")
