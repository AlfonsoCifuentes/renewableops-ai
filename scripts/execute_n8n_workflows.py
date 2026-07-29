"""Import and execute every bounded n8n workflow in the local core profile."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "verification" / "n8n-executions.json"


def _run(arguments: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def main() -> int:
    workflow_paths = sorted((ROOT / "workflows" / "n8n").glob("*.json"))
    imported = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "n8n",
            "n8n",
            "import:workflow",
            "--separate",
            "--input=/workflows",
        ]
    )
    executions: list[dict[str, Any]] = []
    if imported.returncode == 0:
        for path in workflow_paths:
            payload: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            workflow_id = str(payload["id"])
            name = str(payload["name"])
            started = datetime.now(UTC)
            try:
                completed = _run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "-e",
                        "N8N_RUNNERS_ENABLED=false",
                        "n8n",
                        "n8n",
                        "execute",
                        f"--id={workflow_id}",
                        "--rawOutput",
                    ]
                )
                error_tail = completed.stderr.strip().splitlines()[-1:]
                executions.append(
                    {
                        "id": workflow_id,
                        "name": name,
                        "status": "success" if completed.returncode == 0 else "failed",
                        "duration_s": round(
                            (datetime.now(UTC) - started).total_seconds(),
                            3,
                        ),
                        "return_code": completed.returncode,
                        "error_type": error_tail[0][:200] if error_tail else None,
                    }
                )
            except subprocess.TimeoutExpired:
                executions.append(
                    {
                        "id": workflow_id,
                        "name": name,
                        "status": "timeout",
                        "duration_s": 120,
                        "return_code": None,
                        "error_type": "TimeoutExpired",
                    }
                )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": (
            "passed"
            if imported.returncode == 0
            and len(executions) == 6
            and all(item["status"] == "success" for item in executions)
            else "failed"
        ),
        "import": {
            "status": "success" if imported.returncode == 0 else "failed",
            "return_code": imported.returncode,
        },
        "executions": executions,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
