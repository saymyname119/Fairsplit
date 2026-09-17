"""
shared/config.py
─────────────────
Centralised application settings using Pydantic BaseSettings.

Why centralised config?
  Every module that needs a setting imports from here — not from os.environ directly.
  This means:
  - One place to document every env var and its default
  - Type safety (Pydantic coerces and validates at startup, not at runtime)
  - Easy to override in tests: `get_settings.cache_clear(); os.environ["X"] = "Y"`
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Server ────────────────────────────────────────────────
    port: int = Field(default=8000)
    environment: str = Field(default="development")  # development | production | test

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://splitwise:splitwise@localhost:5432/splitwise"
    )

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Auth ──────────────────────────────────────────────────
    jwt_secret: str = Field(default="CHANGE_ME")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_minutes: int = Field(default=60)

    # ── AI ────────────────────────────────────────────────────
    claude_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-sonnet-4-6")

    # ── Cache ─────────────────────────────────────────────────
    balance_cache_ttl_seconds: int = Field(default=300)

    # ── Email Delivery (Resend & SMTP) ─────────────────────────
    resend_api_key: str = Field(default="")
    resend_from_email: str = Field(default="FairSplit <onboarding@resend.dev>")
    app_base_url: str = Field(default="http://localhost:5173")

    # ── SMTP (Free Gmail / Custom SMTP) ───────────────────────
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=465)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="")

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    lru_cache(maxsize=1) means the .env file is read exactly once at startup.
    In tests, call get_settings.cache_clear() then set env vars to override.
    """
    return Settings()
