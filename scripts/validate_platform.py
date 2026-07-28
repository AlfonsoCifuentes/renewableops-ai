"""Run reproducible structural validation for every deployable platform layer."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _resolve(explicit: Path | None, executable: str) -> str | None:
    if explicit:
        return str(explicit.resolve())
    return shutil.which(executable)


def _run(
    name: str,
    command: list[str],
    *,
    cwd: Path = ROOT,
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return {
        "check": name,
        "passed": completed.returncode == 0,
        "command": [Path(command[0]).name, *command[1:]],
        "returncode": completed.returncode,
        "output": combined[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terraform", type=Path)
    parser.add_argument("--kubectl", type=Path)
    parser.add_argument("--helm", type=Path)
    parser.add_argument("--databricks", type=Path)
    args = parser.parse_args()
    terraform = _resolve(args.terraform, "terraform")
    kubectl = _resolve(args.kubectl, "kubectl")
    helm = _resolve(args.helm, "helm")
    databricks = _resolve(args.databricks, "databricks")
    docker = shutil.which("docker")
    results: list[dict[str, Any]] = []

    if docker:
        results.append(_run("docker_compose_config", [docker, "compose", "config", "--quiet"]))
    else:
        results.append(
            {"check": "docker_compose_config", "passed": False, "output": "docker missing"}
        )

    if terraform:
        terraform_dir = ROOT / "infra/terraform/azure"
        results.extend(
            [
                _run(
                    "terraform_format",
                    [terraform, "fmt", "-check", "-recursive"],
                    cwd=terraform_dir,
                ),
                _run("terraform_validate", [terraform, "validate", "-no-color"], cwd=terraform_dir),
            ]
        )
    else:
        results.append(
            {"check": "terraform_validate", "passed": False, "output": "terraform missing"}
        )

    if kubectl:
        results.append(
            _run(
                "kubernetes_kustomize",
                [kubectl, "kustomize", str(ROOT / "infra/kubernetes")],
            )
        )
    else:
        results.append(
            {"check": "kubernetes_kustomize", "passed": False, "output": "kubectl missing"}
        )

    if helm:
        chart = str(ROOT / "infra/helm/renewableops")
        results.extend(
            [
                _run("helm_lint", [helm, "lint", "--strict", chart]),
                _run("helm_template", [helm, "template", "renewableops", chart]),
            ]
        )
    else:
        results.append({"check": "helm_lint", "passed": False, "output": "helm missing"})

    if databricks:
        results.append(
            _run(
                "databricks_bundle_schema",
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_databricks_bundle.py"),
                    databricks,
                ],
            )
        )
    else:
        results.append(
            {
                "check": "databricks_bundle_schema",
                "passed": False,
                "output": "databricks CLI missing",
            }
        )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "local structural validation; no cloud deployment",
        "status": "passed" if all(item["passed"] for item in results) else "failed",
        "checks": results,
    }
    output = ROOT / "artifacts/verification/platform-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
