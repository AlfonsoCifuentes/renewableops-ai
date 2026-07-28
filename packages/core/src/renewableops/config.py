"""Central paths, deterministic seeds and runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(
    os.getenv("RENEWABLEOPS_PROJECT_ROOT", str(Path(__file__).resolve().parents[4]))
).resolve()
DATA_DIR = PROJECT_ROOT / "data"
LAKEHOUSE_DIR = DATA_DIR / "lakehouse"
MODEL_DIR = DATA_DIR / "models"
MANIFEST_DIR = DATA_DIR / "manifests"
PUBLIC_DATA_DIR = PROJECT_ROOT / "apps" / "dashboard" / "public" / "data"
DEFAULT_SEED = 20260728


class Settings(BaseSettings):
    """Environment-backed application settings with safe demo defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_timezone: str = "Europe/Madrid"
    log_level: str = "INFO"
    public_demo: bool = True
    aemet_api_key: str | None = None
    webhook_hmac_secret: str | None = None
    max_upload_bytes: int = 5 * 1024 * 1024


def ensure_directories() -> None:
    """Create only the bounded local directories used by generated artifacts."""

    for path in (
        LAKEHOUSE_DIR / "bronze",
        LAKEHOUSE_DIR / "silver",
        LAKEHOUSE_DIR / "gold",
        MODEL_DIR,
        MANIFEST_DIR,
        PUBLIC_DATA_DIR / "latest",
        PUBLIC_DATA_DIR / "history",
    ):
        path.mkdir(parents=True, exist_ok=True)
