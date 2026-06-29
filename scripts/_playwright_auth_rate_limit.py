"""HuleEdu Playwright login rate-limit helpers.

Domain purpose:
    Parse HuleEdu browser-login RATE_LIMIT responses for authenticated
    Skriptoteket proof scripts without exposing submitted credentials.

Relationships:
    Used by `scripts._playwright_auth` so the canonical login helper can offer
    bounded opt-in backoff while keeping normal auth behavior strict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

HULEEDU_RATE_LIMIT_CODE = "RATE_LIMIT"
RATE_LIMIT_FALLBACK_BACKOFF_MS = 1_000
RATE_LIMIT_DEFAULT_MAX_BACKOFF_MS = 65_000


class LoginResponseProtocol(Protocol):
    status: int
    url: str
    headers: Mapping[str, str]

    def text(self) -> str: ...

    def json(self) -> object: ...


@dataclass(frozen=True)
class _HuleEduRateLimitDetails:
    status: int
    body: str
    limit: int | None
    retry_after_seconds: float | None
    window_seconds: float | None

    def backoff_ms(self, *, max_backoff_ms: int) -> int:
        seconds = (
            self.retry_after_seconds
            if self.retry_after_seconds is not None
            else self.window_seconds
        )
        if seconds is None:
            return min(RATE_LIMIT_FALLBACK_BACKOFF_MS, max_backoff_ms)
        return max(0, min(int(seconds * 1_000), max_backoff_ms))

    def message(self, *, max_backoff_ms: int) -> str:
        details = [
            f"status={self.status}",
            f"error_code={HULEEDU_RATE_LIMIT_CODE}",
            f"backoff_ms={self.backoff_ms(max_backoff_ms=max_backoff_ms)}",
        ]
        if self.limit is not None:
            details.append(f"limit={self.limit}")
        if self.window_seconds is not None:
            details.append(f"window_seconds={self.window_seconds:g}")
        if self.retry_after_seconds is not None:
            details.append(f"retry_after_seconds={self.retry_after_seconds:g}")
        return "HuleEdu login API rate limited: " + " ".join(details) + f": {self.body}"


class HuleEduRateLimitError(AssertionError):
    """Raised when HuleEdu returns a structured login rate-limit response."""

    def __init__(self, details: _HuleEduRateLimitDetails, *, max_backoff_ms: int) -> None:
        self.details = details
        self.max_backoff_ms = max_backoff_ms
        super().__init__(details.message(max_backoff_ms=max_backoff_ms))

    def backoff_ms(self, *, max_backoff_ms: int) -> int:
        """Return the bounded retry delay in milliseconds."""
        return self.details.backoff_ms(max_backoff_ms=max_backoff_ms)


def read_login_response_json(response: LoginResponseProtocol) -> object | None:
    """Read a Playwright response JSON body if it is available."""
    try:
        return response.json()
    except Exception:
        return None


def read_login_response_text(
    response: LoginResponseProtocol,
    *,
    email: str,
    password: str,
) -> str:
    """Read a bounded, credential-redacted Playwright response body."""
    try:
        response_text = response.text()
    except Exception as exc:
        response_text = f"<unavailable: {type(exc).__name__}: {exc}>"
    return _redact_auth_text(response_text[:500], email=email, password=password)


def parse_huleedu_rate_limit_response(
    *,
    response: LoginResponseProtocol,
    response_json: object | None,
    response_text: str,
    max_backoff_ms: int,
) -> HuleEduRateLimitError | None:
    """Return a rate-limit error for HuleEdu RATE_LIMIT responses."""
    data = response_json if isinstance(response_json, Mapping) else {}
    error_code = str(data.get("error_code", "")).upper()
    if response.status != 429 and error_code != HULEEDU_RATE_LIMIT_CODE:
        return None

    details = _HuleEduRateLimitDetails(
        status=response.status,
        body=response_text,
        limit=_optional_int(data.get("limit")),
        retry_after_seconds=_retry_after_seconds(response.headers, data),
        window_seconds=_optional_float(data.get("window_seconds")),
    )
    return HuleEduRateLimitError(details, max_backoff_ms=max_backoff_ms)


def _redact_auth_text(text: str, *, email: str, password: str) -> str:
    redacted = text
    for secret, replacement in ((email, "<email>"), (password, "<password>")):
        if secret:
            redacted = redacted.replace(secret, replacement)
    return redacted


def _retry_after_seconds(
    headers: Mapping[str, str],
    data: Mapping[object, object],
) -> float | None:
    retry_after = _header_value(headers, "retry-after")
    if retry_after is not None:
        parsed = _optional_float(retry_after)
        if parsed is not None:
            return parsed
    for key in ("retry_after_seconds", "retry_after", "retryAfterSeconds"):
        parsed = _optional_float(data.get(key))
        if parsed is not None:
            return parsed
    return None


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _optional_int(value: object) -> int | None:
    number = _optional_float(value)
    if number is None:
        return None
    return int(number)
