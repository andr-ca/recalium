"""Application settings loaded from environment variables via pydantic-settings.

All configuration comes from .env / environment variables.
API keys are NEVER stored here — they are read from environment at validation time only.
"""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars (e.g. CI variables)
    )

    # Database
    database_url: str
    postgres_user: str = "recalium"
    postgres_password: str = "recalium"
    postgres_db: str = "recalium"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Application
    app_env: str = "production"
    log_level: str = "info"
    app_port: int = 8000

    # BYOK keys (optional — empty string means not configured)
    # These are read at runtime for validation only; never persisted to DB.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = ""
    ollama_api_key: str = ""

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        if v not in ("development", "production"):
            raise ValueError(f"app_env must be 'development' or 'production', got: {v!r}")
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
