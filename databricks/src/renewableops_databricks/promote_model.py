# Databricks notebook source
"""Explicit, auditable promotion and rollback for Unity Catalog models."""

import json

import mlflow

dbutils.widgets.text("catalog", "renewableops")
dbutils.widgets.text("schema", "dev")
dbutils.widgets.text("approved_version", "")
dbutils.widgets.dropdown("decision", "hold", ["hold", "promote", "rollback"])

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
approved_version = dbutils.widgets.get("approved_version").strip()
decision = dbutils.widgets.get("decision")
model_name = f"{catalog}.{schema}.renewable_forecast"

mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()

if decision == "promote":
    if not approved_version:
        raise ValueError("approved_version is mandatory for promotion")
    client.set_registered_model_alias(model_name, "Champion", approved_version)
    client.set_model_version_tag(model_name, approved_version, "approval", "human-approved")
elif decision == "rollback":
    previous = client.get_model_version_by_alias(model_name, "Rollback")
    client.set_registered_model_alias(model_name, "Champion", previous.version)

print(
    json.dumps(
        {
            "model": model_name,
            "decision": decision,
            "version": approved_version or None,
            "automatic": False,
        }
    )
)
