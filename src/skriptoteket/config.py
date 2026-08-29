"""Application settings for Skriptoteket.

Purpose:
  Centralize environment-driven configuration for web, workers, curated apps,
  and infrastructure adapters.

Relationships:
  - Loaded by Dishka providers in `skriptoteket.di.*`.
  - Consumed by infrastructure integrations such as Sir Convert-a-Lot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import ParseResult, urlparse, urlunparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LlmReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
LlmTextVerbosity = Literal["low", "medium", "high"]

_CONTAINER_ARTIFACTS_ROOT = Path("/var/lib/skriptoteket/artifacts")
_CONTAINER_VAULT_ROOT = Path("/var/lib/skriptoteket/vault")
_HOST_DEV_ARTIFACTS_ROOT = Path("/tmp/skriptoteket/artifacts")
_HOST_DEV_VAULT_ROOT = Path("/tmp/skriptoteket/vault")
_DOCKER_HOST_ALIASES = frozenset({"host.docker.internal", "gateway.docker.internal"})
_NON_PRODUCTION_ALLOWED_HOSTS = frozenset({"skriptoteket_web", "skriptoteket-web"})


def _is_running_in_container() -> bool:
    return Path("/.dockerenv").exists()


def _replace_url_hostname(*, parsed: ParseResult, hostname: str) -> str:
    userinfo = ""
    if parsed.username is not None:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo = f"{userinfo}:{parsed.password}"
        userinfo = f"{userinfo}@"
    port = f":{parsed.port}" if parsed.port is not None else ""
    return urlunparse(parsed._replace(netloc=f"{userinfo}{hostname}{port}"))


def _normalize_host_dev_sir_convert_base_url(raw_url: str) -> str:
    stripped = raw_url.strip()
    if stripped == "":
        return stripped
    parsed = urlparse(stripped)
    if parsed.hostname not in _DOCKER_HOST_ALIASES:
        return stripped
    return _replace_url_hostname(parsed=parsed, hostname="127.0.0.1")


def _split_csv_values(raw_value: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for part in raw_value.split(","):
        normalized = part.strip()
        if not normalized or normalized in seen:
            continue
        values.append(normalized)
        seen.add(normalized)
    return tuple(values)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Skriptoteket"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "skriptoteket"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    ENABLE_DOCS: bool | None = None
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,::1,skriptoteket.hule.education"
    TRUST_PROXY_HEADERS: bool = False
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32,::1/128"
    PUBLIC_APP_BASE_URL: str = "https://skriptoteket.hule.education"
    CURATED_APPS_PRODUCTION_ALLOWLIST: str = (
        "chemistry.reagent_prep_chef,documents.conversion_hub,classroom.group-seating-studio"
    )

    # Frontend dev server (legacy SSR + SPA islands; ADR-0025 superseded by ADR-0027)
    # If set, templates render SPA assets from the Vite dev server instead of the production
    # manifest.
    VITE_DEV_SERVER_URL: str | None = None

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/skriptoteket"
    DATABASE_ECHO: bool = False
    BOOTSTRAP_SUPERUSER_EMAIL: str = ""
    BOOTSTRAP_SUPERUSER_PASSWORD: str = ""

    DRAFT_LOCK_TTL_SECONDS: int = 60 * 10  # 10 minutes (ADR-0046)

    # Runner (ST-04-02)
    RUNNER_IMAGE: str = "skriptoteket-runner:latest"
    RUNNER_MAX_CONCURRENCY: int = 1
    RUNNER_QUEUE_ENABLED: bool = True
    RUNNER_QUEUE_MAX_ATTEMPTS: int = 1
    RUNNER_QUEUE_LEASE_TTL_SECONDS: int = 60
    RUNNER_QUEUE_HEARTBEAT_INTERVAL_SECONDS: int = 15
    RUNNER_QUEUE_REAPER_INTERVAL_SECONDS: int = 15
    RUNNER_QUEUE_POLL_INTERVAL_SECONDS: float = 1.0
    RUNNER_QUEUE_ADOPT_MISSING_BACKOFF_SECONDS: int = 5
    RUNNER_TIMEOUT_SANDBOX_SECONDS: int = 60
    RUNNER_TIMEOUT_PRODUCTION_SECONDS: int = 120
    RUNNER_CPU_LIMIT: float = 1.0
    RUNNER_MEMORY_LIMIT: str = "1g"
    RUNNER_PIDS_LIMIT: int = 256
    RUNNER_TMPFS_TMP: str = "rw,noexec,nosuid,nodev,size=256m,mode=1777"

    ARTIFACTS_ROOT: Path = Path("/var/lib/skriptoteket/artifacts")
    ARTIFACTS_RETENTION_DAYS: int = 7

    # Reagent Prep Chef: generated SDS PDFs (rendered from markdown, ADR-0067)
    REAGENT_PREP_CHEF_SDS_PDF_CACHE_DIR: Path = Path(
        "/var/lib/skriptoteket/reagent_prep_chef/sds_pdfs"
    )

    # Sir Convert-a-Lot v2 (external conversion engine; EPIC-21 / ADR-0066)
    SIR_CONVERT_A_LOT_V2_BASE_URL: str = "http://127.0.0.1:9010"
    SIR_CONVERT_A_LOT_V2_API_KEY: str = ""
    SIR_CONVERT_A_LOT_V2_UNIX_SOCKET_PATH: str = ""
    SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS: float = 60.0
    SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL: str = ""
    SIR_CONVERT_A_LOT_V2_CLASS_LIST_IMPORT_PDF_BACKEND_STRATEGY: Literal["auto", "pymupdf"] = (
        "pymupdf"
    )
    SIR_CONVERT_A_LOT_V2_CLASS_LIST_IMPORT_ACCELERATION_POLICY: Literal[
        "gpu_required", "gpu_prefer", "cpu_only"
    ] = "cpu_only"

    # Exam Converter conversion lane (EPIC-SKRIPT-39 / ADR-SKRIPT-0090):
    # operator-facing switch between the Sir Convert-backed conversion path
    # and the in-process dxe -> Exam.net bundle walking skeleton.
    EXAM_CONVERTER_CONVERSION_LANE: Literal["sir_convert", "in_process"] = "sir_convert"

    VAULT_ROOT: Path = Path("/var/lib/skriptoteket/vault")
    VAULT_MAX_FILE_BYTES: int = 20_000_000
    VAULT_MAX_TOTAL_BYTES: int = 200_000_000
    VAULT_RETENTION_DAYS: int = 30

    # Platform-only debug capture (OFF by default; see ADR-0051).
    # Captures are written under ARTIFACTS_ROOT and may contain tool code/model output.
    LLM_CAPTURE_ON_ERROR_ENABLED: bool = False
    # Dev-only: capture successful chat-ops responses.
    LLM_CAPTURE_ON_SUCCESS_ENABLED: bool = False

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
    HEALTHZ_DETAILED_RESPONSE: bool | None = None
    METRICS_IDENTITY_GAUGES_ENABLED: bool | None = None

    # Email verification
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    EMAIL_VERIFICATION_BASE_URL: str = "https://skriptoteket.hule.education"

    # Password reset
    PASSWORD_RESET_TTL_HOURS: int = 2
    PASSWORD_RESET_BASE_URL: str = "https://skriptoteket.hule.education"
    PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS: int = 60

    PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS: int = 60
    PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS: int = 5
    PUBLIC_HELPER_IMPORT_PREVIEW_MAX_FILE_BYTES: int = 5_000_000
    PUBLIC_HELPER_IMPORT_PREVIEW_TIMEOUT_SECONDS: int = 15
    PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS: int = 60
    PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS: int = 5
    PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES: int = 1_000_000
    PUBLIC_HELPER_SMART_RUN_TIMEOUT_SECONDS: int = 10
    PUBLIC_HELPER_SHARE_WINDOW_SECONDS: int = 60
    PUBLIC_HELPER_SHARE_MAX_REQUESTS: int = 5
    PUBLIC_HELPER_SHARE_MAX_REQUEST_BYTES: int = 1_000_000
    PUBLIC_HELPER_SHARE_TIMEOUT_SECONDS: int = 10
    PUBLIC_HELPER_SHARE_MAX_RENDERED_BYTES: int = 750_000
    PUBLIC_HELPER_SHARE_MAX_ACTIVE_PER_SNAPSHOT: int = 3
    PUBLIC_HELPER_SHARE_TTL_DAYS: int = 60
    PUBLIC_EXAM_CONVERTER_RATE_LIMIT_WINDOW_SECONDS: int = 60
    PUBLIC_EXAM_CONVERTER_RATE_LIMIT_MAX_REQUESTS: int = 3
    PUBLIC_EXAM_CONVERTER_SOURCE_DXE_MAX_BYTES: int = 20_000_000
    PUBLIC_EXAM_CONVERTER_GRADED_RESULT_PDF_MAX_BYTES: int = 20_000_000
    PUBLIC_EXAM_CONVERTER_AGGREGATE_MAX_BYTES: int = 40_000_000
    PUBLIC_EXAM_CONVERTER_REQUEST_TIME_BUDGET_SECONDS: int = 120
    PUBLIC_EXAM_CONVERTER_CONCURRENCY_LIMIT: int = 1
    PUBLIC_EXAM_CONVERTER_ARTIFACT_TTL_SECONDS: int = 3600
    HULEEDU_PUBLIC_EXAM_CONVERTER_GRANT_BASE_URL: str = ""
    HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ID: str = "skriptoteket-public-exam-converter-backend"
    HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ASSERTION: str = ""
    HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ASSERTION_SECRET: str = ""
    HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ASSERTION_TTL_SECONDS: int = 60
    HULEEDU_PUBLIC_EXAM_CONVERTER_ASSERTION_AUDIENCE: str = ""
    HULEEDU_PUBLIC_EXAM_CONVERTER_TIMEOUT_SECONDS: float = 10.0
    CLASSROOM_SHARE_PREVIEW_MAX_CONCURRENCY: int = 2
    CLASSROOM_SHARE_PREVIEW_TIMEOUT_SECONDS: float = 8.0

    # LLM API
    LLM_COMPLETION_TEMPLATE_ID: str = "inline_completion_v1"
    LLM_COMPLETION_GPT5_TEMPLATE_ID: str = "inline_completion_gpt5_v1"
    LLM_CHAT_TEMPLATE_ID: str = "editor_chat_v1"
    LLM_CHAT_OPS_TEMPLATE_ID: str = "editor_chat_ops_v1"

    # AI policy
    AI_REMOTE_PROVIDERS_ENABLED: bool = True
    AI_DEFAULT_ALLOW_REMOTE_FALLBACK: bool = False

    # HuleEdu Gateway internal identity context verification (ADR-0076 / ADR-0082)
    HULEEDU_INTERNAL_IDENTITY_ISSUER: str = "api_gateway_service"
    HULEEDU_INTERNAL_IDENTITY_AUDIENCE: str | None = None
    HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID: str = "gateway-identity-rs256-v1"
    HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY: str | None = None
    HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH: str | None = None
    HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH: str | None = None
    HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON: str | None = None
    HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS: int = 60
    HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS: int = 5

    # Prompt caching guardrails (OpenAI)
    LLM_PROMPT_CACHE_RETENTION_MODE: Literal["in_memory", "24h"] = "in_memory"
    LLM_PROMPT_CACHE_EXTENDED_ALLOWED: bool = True

    LLM_COMPLETION_ENABLED: bool = False
    LLM_COMPLETION_BASE_URL: str = "http://localhost:8082"
    OPENAI_LLM_COMPLETION_API_KEY: str = ""
    LLM_COMPLETION_PROMPT_CACHE_KEY: str = ""
    LLM_COMPLETION_PROMPT_CACHE_RETENTION: Literal["in_memory", "24h"] | None = None
    LLM_COMPLETION_EXTRA_HEADERS: dict[str, str] = Field(default_factory=dict)
    LLM_COMPLETION_MODEL: str = "Devstral-Small-2-24B"
    LLM_COMPLETION_REASONING_EFFORT: LlmReasoningEffort | None = "minimal"
    LLM_COMPLETION_TEXT_VERBOSITY: LlmTextVerbosity | None = "low"
    LLM_COMPLETION_FALLBACK_BASE_URL: str = ""
    LLM_COMPLETION_FALLBACK_MODEL: str = ""
    LLM_COMPLETION_FALLBACK_REASONING_EFFORT: LlmReasoningEffort | None = None
    LLM_COMPLETION_MAX_TOKENS: int = 64
    LLM_COMPLETION_TEMPERATURE: float = 0.2
    LLM_COMPLETION_TIMEOUT_SECONDS: int = 30
    LLM_COMPLETION_CONTEXT_WINDOW_TOKENS: int = 4096
    LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS: int = 256
    LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS: int = 2048
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
    LLM_CHAT_TEXT_VERBOSITY: LlmTextVerbosity | None = None
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
    LLM_CHAT_OPS_TEXT_VERBOSITY: LlmTextVerbosity | None = None
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

    # Exam answer-key completion (ST-SKRIPT-39-02): GPT-5.6 Luna structured
    # proposals for unkeyed in-process conversions, guarded by the Postgres
    # daily token lease. GLM-5.3-flash via OpenRouter is the failover-only
    # backup; it shares the context/output/timeout/temperature settings and
    # draws from the same daily token lease.
    LLM_ANSWER_KEY_ENABLED: bool = False
    LLM_ANSWER_KEY_BASE_URL: str = "https://api.openai.com"
    OPENAI_LLM_ANSWER_KEY_API_KEY: str = ""
    LLM_ANSWER_KEY_MODEL: str = "gpt-5.6-luna"
    LLM_ANSWER_KEY_FAILOVER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_LLM_ANSWER_KEY_API_KEY: str = ""
    LLM_ANSWER_KEY_FAILOVER_MODEL: str = "z-ai/glm-5.3-flash"
    LLM_ANSWER_KEY_REASONING_EFFORT: LlmReasoningEffort = "low"
    LLM_ANSWER_KEY_TEXT_VERBOSITY: LlmTextVerbosity = "low"
    LLM_ANSWER_KEY_CONTEXT_WINDOW_TOKENS: int = 32_768
    LLM_ANSWER_KEY_MAX_OUTPUT_TOKENS: int = 4_096
    LLM_ANSWER_KEY_TEMPERATURE: float = 0.0
    LLM_ANSWER_KEY_TIMEOUT_SECONDS: int = 90
    LLM_ANSWER_KEY_DAILY_TOKEN_LIMIT: int = 5_000_000
    LLM_ANSWER_KEY_JOB_LEASE_TTL_SECONDS: int = 900

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

    @property
    def curated_apps_production_allowlist(self) -> frozenset[str]:
        return frozenset(_split_csv_values(self.CURATED_APPS_PRODUCTION_ALLOWLIST))

    @property
    def allowed_hosts(self) -> frozenset[str]:
        allowed_hosts = set(_split_csv_values(self.ALLOWED_HOSTS))
        if self.ENVIRONMENT != "production":
            allowed_hosts.update(_NON_PRODUCTION_ALLOWED_HOSTS)
        return frozenset(allowed_hosts)

    @property
    def trusted_proxy_cidrs(self) -> frozenset[str]:
        return frozenset(_split_csv_values(self.TRUSTED_PROXY_CIDRS))

    @property
    def enable_docs(self) -> bool:
        if self.ENABLE_DOCS is None:
            return self.ENVIRONMENT != "production"
        return self.ENABLE_DOCS

    @model_validator(mode="after")
    def _normalize_host_dev_runtime(self) -> Settings:
        if self.ENVIRONMENT != "development" or _is_running_in_container():
            return self

        if self.ARTIFACTS_ROOT == _CONTAINER_ARTIFACTS_ROOT:
            self.ARTIFACTS_ROOT = _HOST_DEV_ARTIFACTS_ROOT
        if self.VAULT_ROOT == _CONTAINER_VAULT_ROOT:
            self.VAULT_ROOT = _HOST_DEV_VAULT_ROOT

        normalized_base_url = _normalize_host_dev_sir_convert_base_url(
            self.SIR_CONVERT_A_LOT_V2_BASE_URL
        )
        if normalized_base_url != self.SIR_CONVERT_A_LOT_V2_BASE_URL:
            self.SIR_CONVERT_A_LOT_V2_BASE_URL = normalized_base_url
        return self

    @property
    def healthz_detailed_response(self) -> bool:
        if self.HEALTHZ_DETAILED_RESPONSE is None:
            return self.ENVIRONMENT != "production"
        return self.HEALTHZ_DETAILED_RESPONSE

    @property
    def metrics_identity_gauges_enabled(self) -> bool:
        if self.METRICS_IDENTITY_GAUGES_ENABLED is None:
            return self.ENVIRONMENT != "production"
        return self.METRICS_IDENTITY_GAUGES_ENABLED
