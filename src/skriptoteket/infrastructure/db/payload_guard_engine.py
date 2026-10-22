"""Bounded engine that holds document payload guards (TASK-SKRIPT-41-01-04).

A payload guard keeps an advisory lock on a connection that is independent of the
request's application session, so the lock survives a failed application COMMIT.
Its connections come from this separate, bounded pool. The pool is counted in the
per-process database budget: ``DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW +
DATABASE_GUARD_POOL_SIZE``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from skriptoteket.config import Settings


@dataclass(frozen=True, slots=True)
class PayloadGuardEngine:
    """Distinct type for the guard engine so DI never confuses it with the app engine."""

    engine: AsyncEngine


def create_payload_guard_engine(settings: Settings) -> PayloadGuardEngine:
    """Create the guard engine; the owner disposes ``engine`` when it closes."""
    return PayloadGuardEngine(
        engine=create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=settings.DATABASE_GUARD_POOL_SIZE,
            max_overflow=0,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
        )
    )


@asynccontextmanager
async def open_payload_guard_engine(settings: Settings) -> AsyncIterator[PayloadGuardEngine]:
    """Create the guard engine for a short-lived process and dispose it on exit."""
    guard_engine = create_payload_guard_engine(settings)
    try:
        yield guard_engine
    finally:
        await guard_engine.engine.dispose()
