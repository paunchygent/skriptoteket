from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LlmReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Skriptoteket"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "skriptoteket"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    ENABLE_DOCS: bool = True

    # Frontend dev server (legacy SSR + SPA islands; ADR-0025 superseded by ADR-0027)
    # If set, templates render SPA assets from the Vite dev server instead of the production
    # manifest.
    VITE_DEV_SERVER_URL: str | None = None

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/skriptoteket"
    DATABASE_ECHO: bool = False

    SESSION_COOKIE_NAME: str = "skriptoteket_session"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    DRAFT_LOCK_TTL_SECONDS: int = 60 * 10  # 10 minutes (ADR-0046)

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

    # Platform-only debug capture (OFF by default; see ADR-0051).
    # Captures are written under ARTIFACTS_ROOT and may contain tool code/model output.
    LLM_CAPTURE_ON_ERROR_ENABLED: bool = False

    LOGIN_EVENTS_RETENTION_DAYS: int = 90

    RUN_OUTPUT_MAX_STDOUT_BYTES: int = 200_000
    RUN_OUTPUT_MAX_STDERR_BYTES: int = 200_000
    RUN_OUTPUT_MAX_HTML_BYTES: int = 500_000
    RUN_OUTPUT_MAX_ERROR_SUMMARY_BYTES: int = 20_000

    UPLOAD_MAX_FILES: int = 20
    UPLOAD_MAX_FILE_BYTES: int = 20_000_000
    UPLOAD_MAX_TOTAL_BYTES: int = 50_000_000

    SESSION_FILES_TTL_SECONDS: int = 60 * 60 * 24  # 24 hours (ADR-0039)
    SANDBOX_SNAPSHOT_TTL_SECONDS: int = 60 * 60 * 24  # 24 hours (ADR-0044)
    SANDBOX_SNAPSHOT_MAX_BYTES: int = 2_000_000  # 2 MB (ADR-0044)

    # Tracing (ST-07-03) - opt-in for monolith
    OTEL_TRACING_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Email (SMTP)
    EMAIL_PROVIDER: Literal["mock", "smtp"] = "mock"
    EMAIL_SMTP_HOST: str = "mail.privateemail.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USERNAME: str = ""
    EMAIL_SMTP_PASSWORD: str = ""
    EMAIL_SMTP_USE_TLS: bool = True
    EMAIL_SMTP_TIMEOUT: int = 30
    EMAIL_DEFAULT_FROM_EMAIL: str = "noreply@hule.education"
    EMAIL_DEFAULT_FROM_NAME: str = "Skriptoteket"
    HEALTHZ_SMTP_CHECK_ENABLED: bool = True

    # Email verification
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    EMAIL_VERIFICATION_BASE_URL: str = "https://skriptoteket.hule.education"

    # LLM API
    LLM_COMPLETION_TEMPLATE_ID: str = "inline_completion_v1"
    LLM_CHAT_TEMPLATE_ID: str = "editor_chat_v1"
    LLM_CHAT_OPS_TEMPLATE_ID: str = "editor_chat_ops_v1"

    LLM_COMPLETION_ENABLED: bool = False
    LLM_COMPLETION_BASE_URL: str = "http://localhost:8082"
    OPENAI_LLM_COMPLETION_API_KEY: str = ""
    LLM_COMPLETION_PROMPT_CACHE_KEY: str = ""
    LLM_COMPLETION_PROMPT_CACHE_RETENTION: Literal["in_memory", "24h"] | None = None
    LLM_COMPLETION_EXTRA_HEADERS: dict[str, str] = Field(default_factory=dict)
    LLM_COMPLETION_MODEL: str = "Devstral-Small-2-24B"
    LLM_COMPLETION_REASONING_EFFORT: LlmReasoningEffort | None = None
    LLM_COMPLETION_MAX_TOKENS: int = 256
    LLM_COMPLETION_TEMPERATURE: float = 0.2
    LLM_COMPLETION_TIMEOUT_SECONDS: int = 30
    LLM_COMPLETION_CONTEXT_WINDOW_TOKENS: int = 4096
    LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS: int = 256
    LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS: int = 1024
    LLM_COMPLETION_PREFIX_MAX_TOKENS: int = 2048
    LLM_COMPLETION_SUFFIX_MAX_TOKENS: int = 512

    LLM_CHAT_ENABLED: bool = False
    LLM_CHAT_BASE_URL: str = "http://localhost:8082"
    OPENAI_LLM_CHAT_API_KEY: str = ""
    LLM_CHAT_PROMPT_CACHE_KEY: str = ""
    LLM_CHAT_PROMPT_CACHE_RETENTION: Literal["in_memory", "24h"] | None = None
    LLM_CHAT_EXTRA_HEADERS: dict[str, str] = Field(default_factory=dict)
    LLM_CHAT_MODEL: str = "Devstral-Small-2-24B"
    LLM_CHAT_REASONING_EFFORT: LlmReasoningEffort | None = None
    # Output token budgets vary significantly between local llama.cpp and GPT-5 thinking models.
    LLM_CHAT_MAX_TOKENS: int = 4 * 1024
    LLM_CHAT_GPT5_MAX_TOKENS: int = 8 * 1024
    LLM_CHAT_TEMPERATURE: float = 0.2
    LLM_CHAT_TIMEOUT_SECONDS: int = 60
    LLM_CHAT_CONTEXT_WINDOW_TOKENS: int = 16384
    LLM_CHAT_GPT5_CONTEXT_WINDOW_TOKENS: int = 64 * 1024
    LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS: int = 256
    LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS: int = 8 * 1024
    LLM_CHAT_TAIL_MAX_MESSAGES: int = 60

    # Chat failover (primary -> fallback). Defaults keep failover disabled.
    LLM_CHAT_FALLBACK_BASE_URL: str = ""
    LLM_CHAT_FALLBACK_MODEL: str = ""
    LLM_CHAT_FALLBACK_REASONING_EFFORT: LlmReasoningEffort | None = None

    LLM_CHAT_OPS_ENABLED: bool = False
    LLM_CHAT_OPS_BASE_URL: str = "http://localhost:8082"
    OPENAI_LLM_CHAT_OPS_API_KEY: str = ""
    LLM_CHAT_OPS_PROMPT_CACHE_KEY: str = ""
    LLM_CHAT_OPS_PROMPT_CACHE_RETENTION: Literal["in_memory", "24h"] | None = None
    LLM_CHAT_OPS_EXTRA_HEADERS: dict[str, str] = Field(default_factory=dict)
    LLM_CHAT_OPS_MODEL: str = "Devstral-Small-2-24B"
    LLM_CHAT_OPS_REASONING_EFFORT: LlmReasoningEffort | None = None
    # Output token budgets vary significantly between local llama.cpp and GPT-5 thinking models.
    LLM_CHAT_OPS_MAX_TOKENS: int = 4 * 1024
    LLM_CHAT_OPS_GPT5_MAX_TOKENS: int = 8 * 1024
    LLM_CHAT_OPS_TEMPERATURE: float = 0.2
    LLM_CHAT_OPS_TIMEOUT_SECONDS: int = 120
    LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS: int = 16 * 1024
    LLM_CHAT_OPS_GPT5_CONTEXT_WINDOW_TOKENS: int = 64 * 1024
    LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS: int = 256
    # Chat-ops prompts include strict JSON-only schema + rules.
    # They are larger than chat-stream prompts.
    LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS: int = 8 * 1024

    LLM_CHAT_OPS_FALLBACK_BASE_URL: str = ""
    LLM_CHAT_OPS_FALLBACK_MODEL: str = ""
    LLM_CHAT_OPS_FALLBACK_REASONING_EFFORT: LlmReasoningEffort | None = None

    LLM_CHAT_FAILOVER_STICKY_TTL_SECONDS: int = 60 * 10  # 10 minutes
    LLM_CHAT_FAILOVER_BREAKER_FAILURE_THRESHOLD: int = 2
    LLM_CHAT_FAILOVER_BREAKER_WINDOW_SECONDS: int = 30
    LLM_CHAT_FAILOVER_BREAKER_COOLDOWN_SECONDS: int = 90
    LLM_CHAT_FAILOVER_PRIMARY_MAX_INFLIGHT: int = 0  # 0 = disabled

    # Tokenizers / prompt budgeting (ST-08-27 / ADR-0055)
    # Devstral (Tekken) tokenizer assets may be set via env and we also auto-detect
    # packaged Tekken assets when `mistral-common` is installed. Missing tokenizers fall back
    # to conservative heuristic counting.
    LLM_DEVSTRAL_TEKKEN_JSON_PATH: Path | None = None

    # Chat template overhead (tokens). These are intentionally conservative defaults and are added
    # in addition to tokenizing message content.
    LLM_GPT5_MESSAGE_OVERHEAD_TOKENS: int = 3
    LLM_GPT5_SYSTEM_MESSAGE_OVERHEAD_TOKENS: int = 3
    LLM_DEVSTRAL_MESSAGE_OVERHEAD_TOKENS: int = 4
    LLM_DEVSTRAL_SYSTEM_MESSAGE_OVERHEAD_TOKENS: int = 4
    LLM_HEURISTIC_MESSAGE_OVERHEAD_TOKENS: int = 4
    LLM_HEURISTIC_SYSTEM_MESSAGE_OVERHEAD_TOKENS: int = 4
