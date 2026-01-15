from __future__ import annotations

import re
from collections.abc import Mapping

from structlog.types import EventDict, WrappedLogger

REDACTED = "[REDACTED]"

_KEY_SPLIT_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

# Base set aligned with `.agent/rules/091-structured-logging.md`,
# normalized to lowercase + underscores.
_SENSITIVE_EXACT_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "x_api_key",
        "authorization",
        "credential",
        "bearer",
        "cookie",
        "session",
        # Common variants (kept tight to avoid over-redaction).
        "session_id",
        "set_cookie",
        "csrf",
        "xsrf",
    }
)

# Segment-based matching to catch keys like `reset_token`, `password_hash`, `bearer_token`, etc.
# NOTE: We intentionally do *not* include `session` as a segment to avoid redacting
# domain identifiers like `tool_session_id`.
_SENSITIVE_SEGMENTS = frozenset(
    {
        "password",
        "passwd",
        "passphrase",
        "secret",
        "token",
        "authorization",
        "credential",
        "bearer",
        "cookie",
        "csrf",
        "xsrf",
    }
)


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def _split_key_segments(key: str) -> tuple[str, ...]:
    normalized = key.strip().lower()
    segments = [segment for segment in _KEY_SPLIT_RE.split(normalized) if segment]
    return tuple(segments)


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SENSITIVE_EXACT_KEYS:
        return True

    segments = _split_key_segments(normalized)
    if not segments:
        return False

    if any(segment in _SENSITIVE_SEGMENTS for segment in segments):
        return True

    # API keys: match `api_key`, `x_api_key`, or segment sequence `api` + `key`.
    if "apikey" in segments:
        return True

    for idx in range(len(segments) - 1):
        if segments[idx] == "api" and segments[idx + 1] == "key":
            return True

    return False


def _looks_like_secret_type(value: object) -> bool:
    # Pydantic secrets expose `get_secret_value()`. Use duck-typing to avoid importing
    # optional types in the hot path.
    getter = getattr(value, "get_secret_value", None)
    return callable(getter)


def _should_redact_value(value: object) -> bool:
    # Keep numeric/bool/None values visible even for sensitive keys (token counts, budgets, etc).
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return False
    return True


def redact_value(value: object) -> object:
    """Recursively redact sensitive values in nested structures.

    This does *not* apply key-based redaction. Use `redact_event_dict` / `redact_sensitive_data`
    for key-aware logic.
    """
    if _looks_like_secret_type(value):
        return REDACTED

    if isinstance(value, Mapping):
        redacted: dict[object, object] = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                redacted[key] = REDACTED if _should_redact_value(item) else item
                continue
            redacted[key] = redact_value(item)
        return redacted

    if isinstance(value, list):
        return [redact_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)

    return value


def redact_event_dict(event_dict: EventDict) -> EventDict:
    """Apply redaction to a structlog event dict."""
    return {
        key: (REDACTED if _should_redact_value(value) else value)
        if _is_sensitive_key(key)
        else redact_value(value)
        for key, value in event_dict.items()
    }


def redact_sensitive_data(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Structlog processor that redacts sensitive values (keys + nested structures)."""
    del logger, method_name
    return redact_event_dict(event_dict)
