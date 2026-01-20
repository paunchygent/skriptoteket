from __future__ import annotations

from urllib.parse import urlparse

import structlog

from skriptoteket.config import Settings

logger = structlog.get_logger(__name__)


def normalize_base_url(*, base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def is_local_llama_server(*, base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.port == 8082 and parsed.hostname in {"localhost", "127.0.0.1"}


def is_openai_api_base_url(*, base_url: str) -> bool:
    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    return hostname.endswith("openai.com")


def supports_gbnf_grammar(*, base_url: str) -> bool:
    """Whether the upstream supports llama.cpp GBNF via the `grammar` request field."""

    parsed = urlparse(base_url)
    return parsed.port == 8082


def merge_headers(*, api_key: str, extra_headers: dict[str, str]) -> dict[str, str]:
    headers: dict[str, str] = dict(extra_headers) if extra_headers else {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def resolve_prompt_cache_retention(
    *,
    settings: Settings,
    configured_retention: str | None,
    allow_prompt_cache_params: bool,
    model: str,
    profile: str,
) -> str | None:
    if not configured_retention or configured_retention == "in_memory":
        return None
    if not allow_prompt_cache_params:
        return None
    if settings.LLM_PROMPT_CACHE_RETENTION_MODE != "24h":
        return None
    if not settings.LLM_PROMPT_CACHE_EXTENDED_ALLOWED:
        logger.info(
            "llm_prompt_cache_retention_suppressed",
            profile=profile,
            model=model,
            retention_mode=settings.LLM_PROMPT_CACHE_RETENTION_MODE,
        )
        return None
    return configured_retention
