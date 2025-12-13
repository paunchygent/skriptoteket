from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Skriptoteket"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    ENABLE_DOCS: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/skriptoteket"
    DATABASE_ECHO: bool = False

    SESSION_COOKIE_NAME: str = "skriptoteket_session"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
