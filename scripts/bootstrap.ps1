$ErrorActionPreference = "Stop"

Write-Host "RenewableOps AI · bootstrap"
uv sync --extra dev --extra platform
npm install
$env:RENEWABLEOPS_ENABLE_MLFLOW = "true"
$env:MLFLOW_TRACKING_URI = "sqlite:///data/mlflow.db"
uv run renewableops run-demo --days 90
uv run pytest
npm run typecheck
npm run test:ui
Write-Host "Ready: npm run dev | uv run uvicorn renewableops_api.main:app --reload --port 8000"
