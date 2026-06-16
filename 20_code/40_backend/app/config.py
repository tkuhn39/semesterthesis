"""
@module: app.config
@context: Central application configuration.
@role: Loads settings from environment / .env into a typed Settings object.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# 20_code/40_backend/app/config.py -> parents[2] == 20_code
_CODE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed runtime configuration sourced from the environment / .env file."""

    app_env: str = "development"
    timezone: str = "Europe/Berlin"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # NoDecode: keep the raw env string so the validator below can split it,
    # instead of pydantic-settings trying to JSON-decode the list.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    output_dir: Path = _CODE_ROOT / "80_output"
    log_dir: Path = _CODE_ROOT / "90_logs"

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


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
