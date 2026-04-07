"""In-memory abuse controls for anonymous public curated-app helper routes.

Purpose:
  Apply a lightweight application-owned rate limit at the public helper API
  boundary without relying on authenticated identities or cookie state.

Relationships:
  - Implements `PublicHelperThrottleProtocol`.
  - Wired through Dishka in `skriptoteket.di.infrastructure.services`.
"""

from __future__ import annotations

import hashlib
import math
from collections import deque
from datetime import datetime, timedelta

from skriptoteket.protocols.public_helpers import (
    PublicHelperThrottleDecision,
    PublicHelperThrottleProtocol,
)


class InMemoryPublicHelperRequestThrottle(PublicHelperThrottleProtocol):
    """Application-scoped rolling-window throttle for anonymous helper requests."""

    def __init__(self) -> None:
        self._request_times_by_key: dict[str, deque[datetime]] = {}

    def evaluate_request(
        self,
        *,
        app_id: str,
        helper_name: str,
        client_ip: str | None,
        user_agent: str | None,
        max_requests: int,
        window_seconds: int,
        now: datetime,
    ) -> PublicHelperThrottleDecision:
        window = timedelta(seconds=window_seconds)
        key = self._key(
            app_id=app_id,
            helper_name=helper_name,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        request_times = self._request_times_by_key.setdefault(key, deque())
        self._prune(request_times=request_times, now=now, window=window)
        if len(request_times) < max_requests:
            return PublicHelperThrottleDecision(is_rate_limited=False)

        oldest_request = request_times[0]
        retry_after = math.ceil((oldest_request + window - now).total_seconds())
        return PublicHelperThrottleDecision(
            is_rate_limited=True,
            retry_after_seconds=max(1, retry_after),
        )

    def record_request(
        self,
        *,
        app_id: str,
        helper_name: str,
        client_ip: str | None,
        user_agent: str | None,
        max_requests: int,
        window_seconds: int,
        now: datetime,
    ) -> None:
        key = self._key(
            app_id=app_id,
            helper_name=helper_name,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        request_times = self._request_times_by_key.setdefault(key, deque())
        self._prune(
            request_times=request_times,
            now=now,
            window=timedelta(seconds=window_seconds),
        )
        request_times.append(now)

    def _key(
        self,
        *,
        app_id: str,
        helper_name: str,
        client_ip: str | None,
        user_agent: str | None,
    ) -> str:
        normalized_ip = (client_ip or "unknown").strip()
        normalized_user_agent = (user_agent or "unknown").strip()[:256]
        fingerprint = hashlib.sha256(
            f"{app_id}\n{helper_name}\n{normalized_ip}\n{normalized_user_agent}".encode("utf-8")
        ).hexdigest()
        return f"{app_id}:{helper_name}:{fingerprint}"

    def _prune(
        self,
        *,
        request_times: deque[datetime],
        now: datetime,
        window: timedelta,
    ) -> None:
        cutoff = now - window
        while request_times and request_times[0] <= cutoff:
            request_times.popleft()
