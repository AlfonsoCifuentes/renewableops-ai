#!/usr/bin/env bash
set -euo pipefail

echo "RenewableOps AI · bootstrap"
uv sync --extra dev --extra platform
npm install
export RENEWABLEOPS_ENABLE_MLFLOW=true
export MLFLOW_TRACKING_URI=sqlite:///data/mlflow.db
uv run renewableops run-demo --days 90
uv run pytest
npm run typecheck
npm run test:ui
echo "Ready: npm run dev | uv run uvicorn renewableops_api.main:app --reload --port 8000"
