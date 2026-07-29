"""Produce bounded acceptance evidence from the local repository state."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml
from renewableops.audit import read_events, verify_chain

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "evidence": evidence}


def main() -> int:
    results: list[dict[str, Any]] = []
    bronze_path = ROOT / "data/lakehouse/bronze/synthetic_scada.parquet"
    silver_path = ROOT / "data/lakehouse/silver/generation.parquet"
    gold_path = ROOT / "data/lakehouse/gold/forecast_evaluation.parquet"
    paths = [bronze_path, silver_path, gold_path]
    results.append(
        check(
            "lakehouse_artifacts",
            all(path.exists() for path in paths),
            [str(path) for path in paths],
        )
    )

    if all(path.exists() for path in paths):
        bronze = pd.read_parquet(bronze_path)
        silver = pd.read_parquet(silver_path)
        gold = pd.read_parquet(gold_path)
        results.extend(
            [
                check("demo_rows", len(silver) == 25_920, len(silver)),
                check(
                    "portfolio_assets",
                    silver["asset_id"].nunique() == 12,
                    int(silver["asset_id"].nunique()),
                ),
                check(
                    "synthetic_disclosure",
                    bool(bronze["is_synthetic"].all()),
                    bool(bronze["is_synthetic"].all()),
                ),
                check(
                    "unique_silver_key",
                    not silver.duplicated(["asset_id", "timestamp_utc"]).any(),
                    len(silver),
                ),
                check(
                    "forecast_quantiles",
                    bool(
                        (gold["p10_mw"] <= gold["p50_mw"]).all()
                        and (gold["p50_mw"] <= gold["p90_mw"]).all()
                    ),
                    len(gold),
                ),
            ]
        )

    manifest_dir = ROOT / "data/manifests"
    manifests = sorted(
        [
            *manifest_dir.glob("*_bronze.json"),
            *manifest_dir.glob("*_silver.json"),
            *manifest_dir.glob("*_gold.json"),
            *manifest_dir.glob("official_*.json"),
        ]
    )
    expected_dataset_ids = {
        "synthetic_scada_bronze",
        "generation_silver",
        "forecast_evaluation_gold",
        "ree_redata_bronze",
        "pvgis_bronze",
        "eurostat_renewables_bronze",
    }
    manifest_valid = True
    manifest_ids: set[str] = set()
    for path in manifests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest_ids.add(str(payload["dataset_id"]))
        artifact_name = {
            "synthetic_scada_bronze": bronze_path,
            "generation_silver": silver_path,
            "forecast_evaluation_gold": gold_path,
        }.get(payload["dataset_id"])
        artifact_relative = payload.get("artifact")
        if artifact_relative:
            artifact_name = ROOT / str(artifact_relative)
        if artifact_name and payload["content_hash"] != f"sha256:{sha256(artifact_name)}":
            manifest_valid = False
    results.append(
        check(
            "manifest_hashes",
            manifest_ids == expected_dataset_ids and manifest_valid,
            {"datasets": sorted(manifest_ids), "valid": manifest_valid},
        )
    )

    source_registry = yaml.safe_load(
        (ROOT / "data/source_registry.yaml").read_text(encoding="utf-8")
    )
    official_sources = [
        source
        for source in source_registry["sources"]
        if source["source_id"] in {"ree_redata", "pvgis", "eurostat_renewables"}
    ]
    results.append(
        check(
            "official_source_registry",
            len(official_sources) == 3 and all(source["enabled"] for source in official_sources),
            [source["source_id"] for source in official_sources],
        )
    )
    source_status_path = manifest_dir / "source_status.json"
    source_status = (
        json.loads(source_status_path.read_text(encoding="utf-8"))
        if source_status_path.exists()
        else {}
    )
    source_evidence = source_status.get("sources", {})
    required_source_ids = {"ree_redata", "pvgis", "eurostat_renewables"}
    successful_source_ids = {
        source_id
        for source_id, evidence in source_evidence.items()
        if source_id in required_source_ids
        and isinstance(evidence, dict)
        and evidence.get("status") == "success"
    }
    results.append(
        check(
            "official_source_ingestion",
            source_status.get("status") == "passed"
            and successful_source_ids == required_source_ids,
            {
                "run_id": source_status.get("run_id"),
                "successful": sorted(successful_source_ids),
            },
        )
    )

    registry_path = ROOT / "data/models/model_registry.json"
    registry = (
        json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    )
    alias_valid = all(
        {"Champion", "Challenger"} <= set(item.get("aliases", {}))
        for item in registry.get("aliases", {}).values()
    )
    results.append(check("model_registry_aliases", alias_valid, str(registry_path)))

    forecast_models = [
        ROOT / "data/models/solar_forecast_champion.joblib",
        ROOT / "data/models/wind_forecast_champion.joblib",
    ]
    cv_model = ROOT / "data/models/cv_solar_champion.joblib"
    model_paths = [*forecast_models, cv_model]
    cv_artifact = joblib.load(cv_model) if cv_model.exists() else None
    cv_estimator = (
        cv_artifact.get("model")
        if isinstance(cv_artifact, dict)
        else cv_artifact
    )
    model_valid = all(
        path.exists() and isinstance(joblib.load(path), dict) for path in forecast_models
    ) and (cv_model.exists() and hasattr(cv_estimator, "predict_proba"))
    results.append(check("model_artifacts", model_valid, [path.name for path in model_paths]))

    mlflow_database = ROOT / "data/mlflow.db"
    mlflow_runs = 0
    if mlflow_database.exists():
        with sqlite3.connect(mlflow_database) as connection:
            mlflow_runs = int(connection.execute("SELECT count(*) FROM runs").fetchone()[0])
    results.append(check("mlflow_tracking", mlflow_runs >= 6, {"runs": mlflow_runs}))

    events = read_events(ROOT / "data/audit/events.jsonl")
    audit_valid, invalid_index = verify_chain(events)
    results.append(
        check(
            "audit_chain",
            audit_valid and len(events) >= 3,
            {"events": len(events), "invalid_index": invalid_index},
        )
    )

    workflow_valid = True
    workflows = sorted((ROOT / "workflows/n8n").glob("*.json"))
    for path in workflows:
        payload = json.loads(path.read_text(encoding="utf-8"))
        workflow_valid &= {"name", "nodes", "connections"} <= payload.keys()
    results.append(check("n8n_workflows", workflow_valid and len(workflows) == 6, len(workflows)))

    public_manifest = ROOT / "apps/dashboard/public/data/manifest.json"
    public_snapshot_valid = public_manifest.exists()
    public_snapshot_evidence: dict[str, Any] = {"path": str(public_manifest)}
    if public_manifest.exists():
        manifest_payload = json.loads(public_manifest.read_text(encoding="utf-8"))
        latest = public_manifest.parent / "latest"
        checksum_valid = all(
            (latest / filename).exists()
            and expected == f"sha256:{sha256(latest / filename)}"
            for filename, expected in manifest_payload.get("files", {}).items()
        )
        dashboard_text = (latest / "dashboard.json").read_text(encoding="utf-8")
        sanitized = not re.search(
            r"(?:[A-Za-z]:\\(?:Users|ProgramData)\\|/(?:home|root|Users)/|"
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16})",
            dashboard_text,
        )
        public_snapshot_valid &= checksum_valid and sanitized
        public_snapshot_evidence.update(
            {
                "files": len(manifest_payload.get("files", {})),
                "checksums": checksum_valid,
                "sanitized": sanitized,
                "sources": manifest_payload.get("sources", []),
            }
        )
    results.append(check("public_snapshot", public_snapshot_valid, public_snapshot_evidence))
    results.append(
        check(
            "docker_compose",
            (ROOT / "docker-compose.yml").exists(),
            "docker compose config validated separately",
        )
    )
    results.append(
        check(
            "databricks_bundle_definition",
            (ROOT / "databricks/databricks.yml").exists(),
            "Lakeflow, Jobs, Unity Catalog and AI/BI resources are versioned",
        )
    )
    platform_report_path = ROOT / "artifacts/verification/platform-validation.json"
    platform_report = (
        json.loads(platform_report_path.read_text(encoding="utf-8"))
        if platform_report_path.exists()
        else {}
    )
    results.append(
        check(
            "platform_structural_validation",
            platform_report.get("status") == "passed",
            {
                "report": str(platform_report_path),
                "checks": [
                    item.get("check")
                    for item in platform_report.get("checks", [])
                    if item.get("passed")
                ],
            },
        )
    )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "status": "passed" if all(item["passed"] for item in results) else "failed",
        "checks": results,
    }
    output = ROOT / "artifacts/verification/report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
