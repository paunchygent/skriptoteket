"""In-memory cooldown service for forgot-password requests.

Purpose:
  Enforce the application-owned normalized-email cooldown required by the
  password-reset slice without leaking account existence through response
  timing or token issuance behavior.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from skriptoteket.protocols.password_reset import PasswordResetRequestThrottleProtocol


class InMemoryPasswordResetRequestThrottle(PasswordResetRequestThrottleProtocol):
    """Application-scoped in-memory cooldown tracker keyed by normalized email."""

    def __init__(self, *, cooldown_seconds: int) -> None:
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._last_request_by_email: dict[str, datetime] = {}

    def is_rate_limited(self, *, normalized_email: str, now: datetime) -> bool:
        self._prune(now=now)
        last_request = self._last_request_by_email.get(normalized_email)
        if last_request is None:
            return False
        return now - last_request < self._cooldown

    def record_request(self, *, normalized_email: str, now: datetime) -> None:
        self._prune(now=now)
        self._last_request_by_email[normalized_email] = now

    def _prune(self, *, now: datetime) -> None:
        cutoff = now - self._cooldown
        expired = [
            normalized_email
            for normalized_email, last_request in self._last_request_by_email.items()
            if last_request <= cutoff
        ]
        for normalized_email in expired:
            self._last_request_by_email.pop(normalized_email, None)
