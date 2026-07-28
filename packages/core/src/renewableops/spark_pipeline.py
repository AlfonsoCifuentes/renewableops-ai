"""PySpark equivalents of the canonical Pandas transformations.

The module imports Spark lazily so the free local core remains lightweight.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


def clean_generation_spark(frame: DataFrame) -> DataFrame:
    """Apply the same UTC, physical-range and deduplication rules as Silver Pandas."""

    from pyspark.sql import functions as fn
    from pyspark.sql.window import Window

    window = Window.partitionBy("asset_id", "timestamp_utc").orderBy(
        fn.col("ingestion_run_id").desc()
    )
    return (
        frame.withColumn("timestamp_utc", fn.to_utc_timestamp("timestamp_utc", "UTC"))
        .withColumn("_row_number", fn.row_number().over(window))
        .where(fn.col("_row_number") == 1)
        .drop("_row_number")
        .withColumn(
            "quality_flag",
            fn.when(
                (fn.col("availability").between(0, 1))
                & (
                    (fn.col("technology") == "battery")
                    | (
                        (fn.col("power_mw") >= -0.001)
                        & (fn.col("power_mw") <= fn.col("installed_capacity_mw") * fn.lit(1.03))
                    )
                ),
                fn.lit("valid"),
            ).otherwise(fn.lit("quarantined")),
        )
    )


def aggregate_portfolio_hourly(frame: DataFrame) -> DataFrame:
    """Build a governed hourly Gold mart at technology and portfolio grain."""

    from pyspark.sql import functions as fn

    return (
        frame.where(fn.col("quality_flag") == "valid")
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


def create_local_spark(app_name: str = "renewableops-local") -> SparkSession:
    """Create a bounded local Spark session for reconciliation and benchmarks."""

    try:
        from pyspark.sql import SparkSession
    except ImportError as error:
        raise RuntimeError("Install the `platform` extra to enable PySpark") from error
    return (
        SparkSession.builder.master("local[2]")
        .appName(app_name)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def spark_available() -> bool:
    """Return whether PySpark and a usable Java home are available."""

    try:
        import pyspark  # noqa: F401
    except ImportError:
        return False
    java_home = os.getenv("JAVA_HOME")
    if sys.platform == "win32":
        return bool(java_home and (Path(java_home) / "bin" / "java.exe").exists())
    return bool(java_home and (Path(java_home) / "bin" / "java").exists())
