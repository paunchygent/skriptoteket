"""Protocols for anonymous public curated-app helper abuse controls.

Purpose:
  Keep public helper throttling protocol-first so public API routes depend on a
  stable anti-abuse seam instead of concrete in-memory storage.

Relationships:
  - Implemented by infrastructure throttles in `skriptoteket.infrastructure`.
  - Consumed by public curated-app API routes under `/api/v1/public/apps/...`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PublicHelperThrottleDecision:
    """Decision returned by a public helper throttle check."""

    is_rate_limited: bool
    retry_after_seconds: int | None = None


class PublicHelperThrottleProtocol(Protocol):
    """Protocol for anonymous public helper abuse controls."""

    def evaluate_request(
        self,
        *,
        app_id: str,
        helper_name: str,
        client_ip: str | None,
        user_agent: str | None,
        now: datetime,
    ) -> PublicHelperThrottleDecision: ...

    def record_request(
        self,
        *,
        app_id: str,
        helper_name: str,
        client_ip: str | None,
        user_agent: str | None,
        now: datetime,
    ) -> None: ...
