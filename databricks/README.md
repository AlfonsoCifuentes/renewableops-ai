# Databricks implementation

This directory is a deployable Declarative Automation Bundle for Databricks
Free Edition or a controlled Azure Databricks workspace. It uses Unity Catalog,
Volumes, Delta tables, Lakeflow pipelines, Lakeflow Jobs, MLflow 3 and an AI/BI
dashboard.

The current 2026 pipeline API is used: `from pyspark import pipelines as dp`.
External HTTP extraction stays outside the pipeline planner; sanitized Parquet
files are uploaded to the landing Volume.

## First run

1. Create a Free Edition workspace and copy its host URL.
2. Install the current Databricks CLI.
3. Authenticate:
   `databricks auth login --host <workspace-url> --profile renewableops-free`.
4. Execute `sql/bootstrap_unity_catalog.sql` in the SQL editor.
5. Upload `data/lakehouse/bronze/synthetic_scada.parquet` to
   `/Volumes/renewableops/dev/landing/scada/`.
6. Set the actual SQL warehouse lookup name in `databricks.yml` if the starter
   warehouse has a different display name.
7. Run:

   ```text
   databricks bundle validate -t dev
   databricks bundle deploy -t dev
   databricks bundle run -t dev daily_renewableops_job
   ```

Schedules ship paused. No paid Azure resource is created and no model is
automatically promoted.
