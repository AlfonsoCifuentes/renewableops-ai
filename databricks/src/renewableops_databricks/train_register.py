# Databricks notebook source
"""Train a bounded sklearn challenger and register it in Unity Catalog."""

# COMMAND ----------
import hashlib
import json

import mlflow
import mlflow.sklearn
import numpy as np
from mlflow.models import infer_signature
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error

dbutils.widgets.text("catalog", "renewableops")
dbutils.widgets.text("schema", "dev")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

dataset = spark.table(f"{catalog}.{schema}.silver_generation").where(
    "technology IN ('solar', 'wind') AND quality_flag = 'valid'"
)
training = (
    dataset.select(
        "timestamp_utc",
        "asset_id",
        "technology",
        "installed_capacity_mw",
        "irradiance_wm2",
        "temperature_c",
        "cloud_cover_fraction",
        "wind_speed_ms",
        "availability",
        "power_mw",
    )
    .orderBy("timestamp_utc")
    .toPandas()
)

cutoff = training["timestamp_utc"].max() - __import__("pandas").Timedelta(days=14)
features = [
    "installed_capacity_mw",
    "irradiance_wm2",
    "temperature_c",
    "cloud_cover_fraction",
    "wind_speed_ms",
    "availability",
]
train = training[training["timestamp_utc"] < cutoff]
test = training[training["timestamp_utc"] >= cutoff]

model = ExtraTreesRegressor(
    n_estimators=120,
    min_samples_leaf=3,
    random_state=20260728,
    n_jobs=-1,
)
model.fit(train[features], train["power_mw"])
prediction = np.clip(model.predict(test[features]), 0, test["installed_capacity_mw"])
mae = float(mean_absolute_error(test["power_mw"], prediction))
dataset_hash = hashlib.sha256(
    training[["timestamp_utc", "asset_id", "power_mw"]].to_csv(index=False).encode()
).hexdigest()

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Shared/renewableops/{schema}/forecast")
with mlflow.start_run(run_name="portfolio_challenger") as run:
    mlflow.log_params({"algorithm": "ExtraTreesRegressor", "split": "blocked_14d"})
    mlflow.log_metrics({"mae_mw": mae, "test_rows": len(test)})
    mlflow.set_tags(
        {
            "dataset_hash": dataset_hash,
            "contains_synthetic_data": "true",
            "promotion_status": "pending_manual_approval",
        }
    )
    signature = infer_signature(test[features], prediction)
    model_info = mlflow.sklearn.log_model(
        sk_model=model,
        name="model",
        signature=signature,
        input_example=test[features].head(3),
        registered_model_name=f"{catalog}.{schema}.renewable_forecast",
    )
    print(json.dumps({"run_id": run.info.run_id, "model_uri": model_info.model_uri, "mae": mae}))
