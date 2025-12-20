from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Skriptoteket"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "skriptoteket"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    ENABLE_DOCS: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/skriptoteket"
    DATABASE_ECHO: bool = False

    SESSION_COOKIE_NAME: str = "skriptoteket_session"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # Runner (ST-04-02)
    RUNNER_IMAGE: str = "skriptoteket-runner:latest"
    RUNNER_MAX_CONCURRENCY: int = 1
    RUNNER_TIMEOUT_SANDBOX_SECONDS: int = 60
    RUNNER_TIMEOUT_PRODUCTION_SECONDS: int = 120
    RUNNER_CPU_LIMIT: float = 1.0
    RUNNER_MEMORY_LIMIT: str = "1g"
    RUNNER_PIDS_LIMIT: int = 256
    RUNNER_TMPFS_TMP: str = "rw,noexec,nosuid,nodev,size=256m,mode=1777"

    ARTIFACTS_ROOT: Path = Path("/var/lib/skriptoteket/artifacts")
    ARTIFACTS_RETENTION_DAYS: int = 7

    RUN_OUTPUT_MAX_STDOUT_BYTES: int = 200_000
    RUN_OUTPUT_MAX_STDERR_BYTES: int = 200_000
    RUN_OUTPUT_MAX_HTML_BYTES: int = 500_000
    RUN_OUTPUT_MAX_ERROR_SUMMARY_BYTES: int = 20_000

    # Tracing (ST-07-03) - opt-in for monolith
    OTEL_TRACING_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
