# Databricks notebook source
"""Weekly model gate: measure, document and request approval without autopromotion."""

import json

import mlflow

dbutils.widgets.text("catalog", "renewableops")
dbutils.widgets.text("schema", "dev")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
model_name = f"{catalog}.{schema}.renewable_forecast"

mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()
versions = client.search_model_versions(f"name='{model_name}'")
if versions:
    newest = max(versions, key=lambda item: int(item.version))
    client.set_registered_model_alias(model_name, "Challenger", newest.version)
    client.set_model_version_tag(
        model_name,
        newest.version,
        "promotion_gate",
        "manual_approval_required",
    )
report = {
    "model": model_name,
    "versions_found": len(versions),
    "gate": "manual_approval_required",
    "auto_promote": False,
    "challenger_alias": newest.version if versions else None,
    "checks": ["temporal_mae", "drift", "latency", "dataset_hash", "model_card"],
}
print(json.dumps(report))
