# Databricks notebook source
"""Export a bounded, sanitized Gold snapshot to a Unity Catalog volume."""

import json

dbutils.widgets.text("catalog", "renewableops")
dbutils.widgets.text("schema", "dev")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
output = f"/Volumes/{catalog}/{schema}/snapshots/latest"

rows = (
    spark.table(f"{catalog}.{schema}.gold_portfolio_hourly")
    .orderBy("date_hour", ascending=False)
    .limit(336)
    .toPandas()
)
payload = {
    "snapshot_version": "1.0.0",
    "is_demo": True,
    "contains_synthetic_data": True,
    "rows": json.loads(rows.to_json(orient="records", date_format="iso")),
}
dbutils.fs.mkdirs(output)
dbutils.fs.put(f"{output}/overview.json", json.dumps(payload, allow_nan=False), True)
print(f"Wrote {len(rows)} sanitized rows to {output}")
