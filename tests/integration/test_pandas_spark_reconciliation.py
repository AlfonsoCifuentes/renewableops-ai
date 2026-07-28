from __future__ import annotations

import pandas as pd
import pytest
from renewableops.spark_pipeline import (
    aggregate_portfolio_hourly,
    clean_generation_spark,
    create_local_spark,
    spark_available,
)
from renewableops.synthetic import generate_scada


@pytest.mark.integration
@pytest.mark.skipif(
    not spark_available(), reason="PySpark optional platform extra is not installed"
)
def test_pandas_and_spark_reconcile_hourly_totals() -> None:
    pandas_frame = generate_scada(days=2)
    spark = create_local_spark("renewableops-reconciliation-test")
    try:
        spark_frame = spark.createDataFrame(pandas_frame)
        gold = aggregate_portfolio_hourly(clean_generation_spark(spark_frame)).toPandas()
        gold["date_hour"] = pd.to_datetime(gold["date_hour"], utc=True)
        expected = (
            pandas_frame.groupby(["timestamp_utc", "technology"], observed=True)["energy_mwh"]
            .sum()
            .reset_index()
            .rename(columns={"timestamp_utc": "date_hour"})
        )
        merged = expected.merge(
            gold[["date_hour", "technology", "energy_mwh"]],
            on=["date_hour", "technology"],
            suffixes=("_pandas", "_spark"),
        )
        assert (merged["energy_mwh_pandas"] - merged["energy_mwh_spark"]).abs().max() < 1e-6
    finally:
        spark.stop()
