"""Document payload guard for the user vault repository.

A payload guard excludes concurrent payload readers and writers of one exam
document until its SQL commit and any filesystem compensation have finished.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.db.payload_guard_engine import PayloadGuardEngine


def advisory_lock_id(key: str) -> int:
    """Return the stable, namespaced signed bigint of an advisory lock key."""
    return int.from_bytes(blake2b(key.encode(), digest_size=8).digest(), signed=True)


class VaultPayloadGuard:
    """Holds a payload advisory lock on a bounded guard connection."""

    def __init__(self, *, session: AsyncSession, guard_engine: PayloadGuardEngine) -> None:
        self._session = session
        self._guard_engine = guard_engine

    @asynccontextmanager
    async def hold(self, *, user_id: UUID, document_lineage_id: UUID) -> AsyncIterator[None]:
        # An independent, rollback-only connection retains this lock even when
        # the application COMMIT fails and releases its transaction locks.
        lock_id = advisory_lock_id(f"vault:payload:{user_id}:{document_lineage_id}")
        # Own the application connection before waiting for a guard connection.
        # A guard holder then never waits on the application pool, so the guard
        # pool and the application pool cannot wait on each other. Guard
        # connections are pooled and bounded by DATABASE_GUARD_POOL_SIZE, which
        # the per-process database budget counts on top of the application pool.
        await self._session.connection()
        async with self._guard_engine.engine.connect() as connection:
            await connection.execute(select(func.pg_advisory_xact_lock(lock_id)))
            yield
            # Connection.close rolls back; repositories never commit application data.
