"""
@module: app.config
@context: Central application configuration (the single .env contract).
@role: Loads every endpoint, credential and path from the one 20_code/.env into
       a typed, validated Settings object. This is the ONLY place the app reads
       environment configuration; nothing is hardcoded elsewhere
       (see project_rules.md §15-17).
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# 20_code/40_backend/app/config.py -> parents[2] == 20_code
_CODE_ROOT = Path(__file__).resolve().parents[2]

StorageBackend = Literal["local", "s3"]
DatabaseBackend = Literal["none", "sqlite", "postgres", "d1"]


class PublicSummary(TypedDict):
    """Non-secret configuration overview (safe to expose via the API)."""

    app_env: str
    node_name: str
    storage_backend: str
    database_backend: str


class Settings(BaseSettings):
    """Typed runtime configuration sourced from the environment / .env file."""

    # --- General -------------------------------------------------------------
    app_env: Literal["development", "production"] = "development"
    # Identifies the process/node in logs; relevant once running on many nodes.
    node_name: str = "local"
    timezone: str = "Europe/Berlin"
    log_level: str = "INFO"
    # 12-factor: log to stdout so a multi-node deployment can aggregate logs.
    log_to_stdout: bool = True

    # --- Paths (overridable via .env, never hardcoded elsewhere) -------------
    # Disposable cache (mesh/FE intermediates); safe to delete at any time.
    # Persisted results go through app.storage (STORAGE_LOCAL_BASE_PATH), not here.
    cache_dir: Path = _CODE_ROOT / "60_cache"
    log_dir: Path = _CODE_ROOT / "90_logs"

    # --- API -----------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # NoDecode: keep the raw env string so the validator below can split it,
    # instead of pydantic-settings trying to JSON-decode the list.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # --- Object / file storage ----------------------------------------------
    # "local" = a directory (single-node/dev). "s3" = any S3-compatible service
    # (AWS S3, Cloudflare R2, Ceph radosgw, MinIO) via s3_endpoint_url.
    storage_backend: StorageBackend = "local"
    storage_local_base_path: Path = _CODE_ROOT / "80_output"
    s3_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    # R2/Ceph/MinIO generally need path-style addressing.
    s3_use_path_style: bool = True

    # --- Database (extension point; see app/database) ------------------------
    database_backend: DatabaseBackend = "none"
    database_url: SecretStr | None = None  # sqlite/postgres DSN (may hold creds)
    d1_account_id: str | None = None
    d1_database_id: str | None = None
    d1_api_token: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=_CODE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string for CORS_ORIGINS."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def public_summary(self) -> PublicSummary:
        """Non-secret configuration overview (safe to expose via the API)."""
        return {
            "app_env": self.app_env,
            "node_name": self.node_name,
            "storage_backend": self.storage_backend,
            "database_backend": self.database_backend,
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
