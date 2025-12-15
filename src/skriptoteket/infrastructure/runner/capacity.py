from __future__ import annotations

import asyncio


class RunnerCapacityLimiter:
    """Concurrency limiter with immediate rejection (ADR-0016: cap + reject, no queue)."""

    def __init__(self, *, max_concurrency: int) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._max_concurrency = max_concurrency
        self._available = max_concurrency
        self._lock = asyncio.Lock()

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self._available <= 0:
                return False
            self._available -= 1
            return True

    async def release(self) -> None:
        async with self._lock:
            self._available += 1
            if self._available > self._max_concurrency:
                raise RuntimeError("RunnerCapacityLimiter released too many times")
