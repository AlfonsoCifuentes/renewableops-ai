"""Capture bounded evidence from the live local container profiles."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _http(name: str, url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return {
                "check": name,
                "passed": response.status == 200,
                "status": response.status,
                "body": body,
            }
    except Exception as error:  # noqa: BLE001 - verification reports bounded failure details
        return {"check": name, "passed": False, "error": type(error).__name__}


def _prometheus_targets() -> dict[str, Any]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/targets", timeout=5) as response:
            payload = json.load(response)
        targets = {
            item["labels"]["job"]: item["health"] for item in payload["data"]["activeTargets"]
        }
        return {
            "check": "prometheus_targets",
            "passed": targets.get("renewableops-api") == "up",
            "targets": targets,
        }
    except Exception as error:  # noqa: BLE001 - bounded verification
        return {"check": "prometheus_targets", "passed": False, "error": type(error).__name__}


def _grafana_dashboard() -> dict[str, Any]:
    password = os.getenv("GRAFANA_ADMIN_PASSWORD", "renewableops_local_only")
    credentials = base64.b64encode(f"admin:{password}".encode()).decode()
    request = urllib.request.Request(
        "http://127.0.0.1:3001/api/search",
        headers={"Authorization": f"Basic {credentials}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
        dashboards = {
            item.get("uid"): item.get("title") for item in payload if item.get("type") == "dash-db"
        }
        return {
            "check": "grafana_provisioning",
            "passed": dashboards.get("renewableops-health") is not None,
            "dashboards": dashboards,
        }
    except Exception as error:  # noqa: BLE001 - bounded verification
        return {"check": "grafana_provisioning", "passed": False, "error": type(error).__name__}


def _n8n_database() -> dict[str, Any]:
    query = (
        "SELECT (SELECT count(*) FROM workflow_entity),"
        "COALESCE((SELECT status FROM execution_entity ORDER BY id DESC LIMIT 1),'none');"
    )
    completed = subprocess.run(
        [
            "docker",
            "exec",
            "renewableops-ai-postgres-1",
            "psql",
            "-U",
            "renewableops",
            "-d",
            "renewableops",
            "-Atc",
            query,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout.strip()
    fields = output.split("|")
    count = int(fields[0]) if fields and fields[0].isdigit() else 0
    status = fields[1] if len(fields) > 1 else "unknown"
    return {
        "check": "n8n_import_and_execution",
        "passed": completed.returncode == 0 and count >= 6 and status == "success",
        "imported_workflows": count,
        "latest_execution_status": status,
    }


def main() -> int:
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "--profile",
            "core",
            "--profile",
            "monitoring",
            "ps",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    containers = [
        json.loads(line) for line in completed.stdout.splitlines() if line.strip().startswith("{")
    ]
    expected = {
        "api",
        "dashboard",
        "grafana",
        "loki",
        "minio",
        "mlflow",
        "n8n",
        "postgres",
        "prometheus",
    }
    by_service = {item["Service"]: item for item in containers}
    container_check = {
        "check": "container_profiles",
        "passed": (
            expected <= set(by_service)
            and all(by_service[name]["State"] == "running" for name in expected)
            and all(
                by_service[name]["Health"] == "healthy"
                for name in {"api", "dashboard", "minio", "mlflow", "postgres"}
            )
        ),
        "services": {
            name: {
                "state": by_service.get(name, {}).get("State"),
                "health": by_service.get(name, {}).get("Health"),
                "ports": by_service.get(name, {}).get("Ports"),
            }
            for name in sorted(expected)
        },
    }
    checks = [
        container_check,
        _http("api_ready", "http://127.0.0.1:8000/health/ready"),
        _http("dashboard_health", "http://127.0.0.1:3000/api/health"),
        _http("n8n_health", "http://127.0.0.1:5678/healthz"),
        _http("grafana_health", "http://127.0.0.1:3001/api/health"),
        _http("prometheus_ready", "http://127.0.0.1:9090/-/ready"),
        _prometheus_targets(),
        _grafana_dashboard(),
        _n8n_database(),
    ]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "live local Docker core + monitoring profiles",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "checks": checks,
    }
    output = ROOT / "artifacts/verification/container-runtime.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
