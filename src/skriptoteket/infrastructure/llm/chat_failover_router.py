from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from uuid import UUID

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverProvider,
    ChatFailoverRouterProtocol,
)


@dataclass(slots=True)
class _BreakerState:
    open_until_monotonic: float = 0.0
    failure_timestamps_monotonic: deque[float] = field(default_factory=deque)


class InProcessChatFailoverRouter(ChatFailoverRouterProtocol):
    """In-process failover routing state (best-effort, not for correctness)."""

    def __init__(self, *, settings: Settings) -> None:
        self._lock = asyncio.Lock()
        self._sticky_until: dict[tuple[UUID, UUID], float] = {}

        self._failure_threshold = settings.LLM_CHAT_FAILOVER_BREAKER_FAILURE_THRESHOLD
        self._failure_window_seconds = settings.LLM_CHAT_FAILOVER_BREAKER_WINDOW_SECONDS
        self._cooldown_seconds = settings.LLM_CHAT_FAILOVER_BREAKER_COOLDOWN_SECONDS
        self._sticky_ttl_seconds = settings.LLM_CHAT_FAILOVER_STICKY_TTL_SECONDS
        self._primary_max_inflight = settings.LLM_CHAT_FAILOVER_PRIMARY_MAX_INFLIGHT

        self._primary_breaker = _BreakerState()
        self._fallback_breaker = _BreakerState()
        self._primary_inflight = 0
        self._fallback_inflight = 0

    def _now(self) -> float:
        return time.monotonic()

    def _prune_failures(self, *, state: _BreakerState, now: float) -> None:
        while state.failure_timestamps_monotonic and (
            now - state.failure_timestamps_monotonic[0] > self._failure_window_seconds
        ):
            state.failure_timestamps_monotonic.popleft()

    def _is_breaker_open(self, *, state: _BreakerState, now: float) -> bool:
        return state.open_until_monotonic > now

    def _maybe_open_breaker(self, *, state: _BreakerState, now: float) -> None:
        self._prune_failures(state=state, now=now)
        if len(state.failure_timestamps_monotonic) < self._failure_threshold:
            return
        state.open_until_monotonic = now + self._cooldown_seconds
        state.failure_timestamps_monotonic.clear()

    def _prune_sticky(self, *, now: float) -> None:
        expired = [key for key, until in self._sticky_until.items() if until <= now]
        for key in expired:
            self._sticky_until.pop(key, None)

    def _primary_is_overloaded(self) -> bool:
        if self._primary_max_inflight <= 0:
            return False
        return self._primary_inflight >= self._primary_max_inflight

    async def decide_route(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        allow_remote_fallback: bool,
        fallback_available: bool,
        fallback_is_remote: bool,
    ) -> ChatFailoverDecision:
        now = self._now()
        key = (user_id, tool_id)

        async with self._lock:
            self._prune_sticky(now=now)

            fallback_breaker_open = self._is_breaker_open(state=self._fallback_breaker, now=now)
            primary_breaker_open = self._is_breaker_open(state=self._primary_breaker, now=now)

            sticky_active = self._sticky_until.get(key, 0.0) > now

            if (
                sticky_active
                and fallback_available
                and not fallback_breaker_open
                and (allow_remote_fallback or not fallback_is_remote)
            ):
                return ChatFailoverDecision(provider="fallback", reason="sticky_fallback")

            if primary_breaker_open and fallback_available and not fallback_breaker_open:
                if fallback_is_remote and not allow_remote_fallback:
                    return ChatFailoverDecision(
                        provider="fallback",
                        reason="breaker_open",
                        blocked="remote_fallback_required",
                    )
                return ChatFailoverDecision(provider="fallback", reason="breaker_open")

            if (
                self._primary_is_overloaded()
                and fallback_available
                and not fallback_breaker_open
                and (allow_remote_fallback or not fallback_is_remote)
            ):
                return ChatFailoverDecision(provider="fallback", reason="load_shed")

            return ChatFailoverDecision(provider="primary", reason="primary_default")

    async def acquire_inflight(self, *, provider: ChatFailoverProvider) -> None:
        async with self._lock:
            if provider == "primary":
                self._primary_inflight += 1
            else:
                self._fallback_inflight += 1

    async def release_inflight(self, *, provider: ChatFailoverProvider) -> None:
        async with self._lock:
            if provider == "primary":
                self._primary_inflight = max(0, self._primary_inflight - 1)
            else:
                self._fallback_inflight = max(0, self._fallback_inflight - 1)

    async def record_success(self, *, provider: ChatFailoverProvider) -> None:
        now = self._now()
        async with self._lock:
            state = self._primary_breaker if provider == "primary" else self._fallback_breaker
            state.open_until_monotonic = 0.0
            state.failure_timestamps_monotonic.clear()
            self._prune_failures(state=state, now=now)

    async def record_failure(self, *, provider: ChatFailoverProvider) -> None:
        now = self._now()
        async with self._lock:
            state = self._primary_breaker if provider == "primary" else self._fallback_breaker
            if self._is_breaker_open(state=state, now=now):
                return
            state.failure_timestamps_monotonic.append(now)
            self._maybe_open_breaker(state=state, now=now)

    async def mark_fallback_used(self, *, user_id: UUID, tool_id: UUID) -> None:
        now = self._now()
        async with self._lock:
            self._sticky_until[(user_id, tool_id)] = now + self._sticky_ttl_seconds
