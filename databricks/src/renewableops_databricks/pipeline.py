# Databricks notebook source
"""Lakeflow pipeline: incremental Bronze, governed Silver and operational Gold."""

from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as fn

LANDING_PATH = spark.conf.get("renewableops.landing_path")

SILVER_EXPECTATIONS = {
    "asset_id_present": "asset_id IS NOT NULL",
    "timestamp_present": "timestamp_utc IS NOT NULL",
    "availability_range": "availability BETWEEN 0 AND 1",
    "known_technology": "technology IN ('solar', 'wind', 'battery')",
}


@dp.table(
    name="bronze_scada",
    comment="Immutable synthetic SCADA landing stream with source metadata.",
    table_properties={
        "quality": "bronze",
        "data_classification": "public_synthetic",
        "pipelines.autoOptimize.managed": "true",
    },
)
def bronze_scada():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(LANDING_PATH)
        .withColumn("_ingested_at", fn.current_timestamp())
        .withColumn("_source_file", fn.input_file_name())
    )


@dp.materialized_view(
    name="silver_generation",
    comment="UTC-normalized, typed and deduplicated generation records.",
    table_properties={"quality": "silver"},
)
@dp.expect_all(SILVER_EXPECTATIONS)
@dp.expect_or_drop(
    "physical_power_range",
    """
    technology = 'battery'
    OR (power_mw >= -0.001 AND power_mw <= installed_capacity_mw * 1.03)
    """,
)
def silver_generation():
    window = Window.partitionBy("asset_id", "timestamp_utc").orderBy(fn.col("_ingested_at").desc())
    return (
        spark.read.table("bronze_scada")
        .withColumn("timestamp_utc", fn.to_utc_timestamp("timestamp_utc", "UTC"))
        .withColumn("_row_number", fn.row_number().over(window))
        .where(fn.col("_row_number") == 1)
        .drop("_row_number")
        .withColumn("quality_flag", fn.lit("valid"))
    )


@dp.materialized_view(
    name="quarantine_generation",
    comment="Records retained for review after a physical or schema violation.",
    table_properties={"quality": "quarantine"},
)
def quarantine_generation():
    return spark.read.table("bronze_scada").where(
        (fn.col("asset_id").isNull())
        | (fn.col("timestamp_utc").isNull())
        | (~fn.col("availability").between(0, 1))
        | (
            (fn.col("technology") != "battery")
            & (
                (fn.col("power_mw") < -0.001)
                | (fn.col("power_mw") > fn.col("installed_capacity_mw") * fn.lit(1.03))
            )
        )
    )


@dp.materialized_view(
    name="gold_portfolio_hourly",
    comment="Hourly operations mart at technology grain.",
    table_properties={"quality": "gold", "semantic_grain": "technology_hour"},
    cluster_by=["date_hour", "technology"],
)
@dp.expect_or_fail("non_negative_energy", "energy_mwh >= 0")
def gold_portfolio_hourly():
    return (
        spark.read.table("silver_generation")
        .where((fn.col("quality_flag") == "valid") & (fn.col("technology") != "battery"))
        .withColumn("date_hour", fn.date_trunc("hour", "timestamp_utc"))
        .groupBy("date_hour", "technology")
        .agg(
            fn.sum("energy_mwh").alias("energy_mwh"),
            fn.sum("power_mw").alias("actual_mw"),
            fn.sum("expected_power_mw").alias("expected_mw"),
            fn.avg("availability").alias("availability"),
            fn.avg("price_eur_mwh").alias("price_eur_mwh"),
            fn.countDistinct("asset_id").alias("asset_count"),
        )
        .withColumn(
            "mwh_at_risk",
            fn.greatest(fn.col("expected_mw") - fn.col("actual_mw"), fn.lit(0.0)),
        )
    )
