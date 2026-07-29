.PHONY: bootstrap seed ingest-demo scale-data transform train serve dashboard test lint security sbom verify publish-snapshot demo services-up services-down n8n-import n8n-smoke databricks-auth databricks-bootstrap databricks-upload-demo databricks-validate databricks-deploy databricks-run databricks-export-snapshot

bootstrap:
	uv sync --extra dev --extra platform --extra cv
	npm install

seed:
	RENEWABLEOPS_ENABLE_MLFLOW=true MLFLOW_TRACKING_URI=sqlite:///data/mlflow.db uv run renewableops run-demo

ingest-demo:
	uv run renewableops ingest

scale-data:
	uv run renewableops generate-scale --days 730 --frequency 5min

transform:
	uv run renewableops transform

train:
	uv run renewableops train

serve:
	uv run uvicorn renewableops_api.main:app --reload --port 8000

dashboard:
	npm run dev

test:
	uv run pytest
	npm run typecheck
	npm run test:ui

lint:
	uv run ruff check .
	npm run lint

security:
	uv run pip-audit
	npm audit --audit-level=critical
	uv run bandit -r packages apps/api/src scripts -x tests -lll -q
	uv run python scripts/scan_secrets.py

sbom:
	uv run python scripts/generate_sbom.py

verify:
	uv run python scripts/verify_environment.py
	uv run python scripts/validate_n8n_workflows.py
	docker compose config --quiet

publish-snapshot:
	uv run renewableops publish

demo:
	RENEWABLEOPS_ENABLE_MLFLOW=true MLFLOW_TRACKING_URI=sqlite:///data/mlflow.db uv run renewableops run-demo

services-up:
	docker compose --profile core up -d

services-down:
	docker compose --profile core down

n8n-import:
	docker compose exec n8n n8n import:workflow --separate --input=/workflows

n8n-smoke:
	uv run python scripts/execute_n8n_workflows.py

databricks-auth:
	databricks auth login --profile renewableops-free

databricks-bootstrap:
	@echo "Execute databricks/sql/bootstrap_unity_catalog.sql once in the workspace SQL editor."

databricks-upload-demo:
	databricks fs cp data/lakehouse/bronze/synthetic_scada.parquet dbfs:/Volumes/renewableops/dev/landing/scada/synthetic_scada.parquet --profile renewableops-free --overwrite

databricks-validate:
	cd databricks && databricks bundle validate -t dev

databricks-deploy:
	cd databricks && databricks bundle deploy -t dev

databricks-run:
	cd databricks && databricks bundle run daily_renewableops_job -t dev

databricks-export-snapshot:
	cd databricks && databricks bundle run snapshot_export_job -t dev
