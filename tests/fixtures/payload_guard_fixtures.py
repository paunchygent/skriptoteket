"""Payload guard engines for tests that build the vault repository directly."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from skriptoteket.infrastructure.db.payload_guard_engine import PayloadGuardEngine


def unpooled_payload_guard_engine(bind: AsyncEngine | AsyncConnection | None) -> PayloadGuardEngine:
    """Guard engine on the database of ``bind``, holding no connection between guards.

    Tests that do not measure the guard pool use this so a guard never waits on a
    shared pool. The pool and its budget are covered by their own integration test.
    """
    if bind is None:
        raise RuntimeError("A payload guard requires a bound database engine.")
    engine = bind.engine if isinstance(bind, AsyncConnection) else bind
    return PayloadGuardEngine(engine=create_async_engine(engine.url, poolclass=NullPool))
