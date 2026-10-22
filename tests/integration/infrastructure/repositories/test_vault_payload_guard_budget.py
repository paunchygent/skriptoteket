"""Payload guards draw from a bounded guard pool that the DB budget counts.

TASK-SKRIPT-41-01-04 review finding F4. A payload guard used to open an unpooled
connection per call, so concurrent guards escaped the declared per-process
connection budget. A guard now checks out one of ``DATABASE_GUARD_POOL_SIZE``
pooled connections, after the request already owns its application connection.
These tests hold real guards open against PostgreSQL and count server-side
connections.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from skriptoteket.config import Settings
from skriptoteket.infrastructure.db.payload_guard_engine import (
    PayloadGuardEngine,
    create_payload_guard_engine,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_APP_POOL_SIZE = 2
_GUARD_POOL_SIZE = 1
# One application connection per request plus the shared guard pool.
_DECLARED_BUDGET = _APP_POOL_SIZE + _GUARD_POOL_SIZE
_WAIT_SECONDS = 0.4

_SERVER_CONNECTIONS = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE datname = current_database() AND pid <> pg_backend_pid()"
)


@dataclass(frozen=True, slots=True)
class Harness:
    app_engine: AsyncEngine
    guard_engine: PayloadGuardEngine
    sessions: async_sessionmaker[AsyncSession]
    observer: AsyncEngine
    baseline: int

    def repository(self, session: AsyncSession) -> PostgreSQLUserVaultFileRepository:
        return PostgreSQLUserVaultFileRepository(session, self.guard_engine)

    async def connections(self) -> int:
        async with self.observer.connect() as connection:
            count: int = (await connection.execute(_SERVER_CONNECTIONS)).scalar_one()
        return count - self.baseline


@asynccontextmanager
async def _harness(database_url: str, *, guard_timeout: float = 5.0) -> AsyncIterator[Harness]:
    observer = create_async_engine(database_url, poolclass=NullPool)
    async with observer.connect() as connection:
        baseline: int = (await connection.execute(_SERVER_CONNECTIONS)).scalar_one()
    app_engine = create_async_engine(
        database_url, pool_size=_APP_POOL_SIZE, max_overflow=0, pool_timeout=5
    )
    guard_engine = create_payload_guard_engine(
        Settings(
            DATABASE_URL=database_url,
            DATABASE_GUARD_POOL_SIZE=_GUARD_POOL_SIZE,
            DATABASE_POOL_TIMEOUT_SECONDS=guard_timeout,
        )
    )
    try:
        yield Harness(
            app_engine=app_engine,
            guard_engine=guard_engine,
            sessions=async_sessionmaker(app_engine, expire_on_commit=False, class_=AsyncSession),
            observer=observer,
            baseline=baseline,
        )
    finally:
        await guard_engine.engine.dispose()
        await app_engine.dispose()
        await observer.dispose()


def _checked_out(engine: AsyncEngine) -> int:
    pool = engine.pool
    assert isinstance(pool, QueuePool)
    return pool.checkedout()


async def _hold_guard(
    harness: Harness,
    *,
    lineage_id: UUID,
    entered: asyncio.Event,
    release: asyncio.Event,
    own_connection_first: bool = False,
) -> None:
    async with harness.sessions() as session:
        if own_connection_first:
            await session.connection()
        repository = harness.repository(session)
        async with repository.guard_document_payload(
            user_id=uuid4(), document_lineage_id=lineage_id
        ):
            entered.set()
            await release.wait()


async def test_second_guard_waits_for_the_pool_and_the_total_stays_in_budget(
    migrated_db: str,
) -> None:
    async with _harness(migrated_db) as harness:
        first_entered, second_entered = asyncio.Event(), asyncio.Event()
        release_first, release_second = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(
            _hold_guard(harness, lineage_id=uuid4(), entered=first_entered, release=release_first)
        )
        async with asyncio.timeout(5):
            await first_entered.wait()
        # A different lineage takes a different advisory lock, so only the
        # bounded guard pool can make the second guard wait.
        second = asyncio.create_task(
            _hold_guard(harness, lineage_id=uuid4(), entered=second_entered, release=release_second)
        )
        await asyncio.sleep(_WAIT_SECONDS)

        assert not second_entered.is_set()
        assert await harness.connections() <= _DECLARED_BUDGET

        release_first.set()
        async with asyncio.timeout(5):
            await second_entered.wait()
        assert await harness.connections() <= _DECLARED_BUDGET
        release_second.set()
        await asyncio.gather(first, second)
        assert await harness.connections() <= _APP_POOL_SIZE + _GUARD_POOL_SIZE


async def test_guard_waiting_with_its_application_connection_proceeds_after_release(
    migrated_db: str,
) -> None:
    async with _harness(migrated_db) as harness:
        first_entered, second_entered = asyncio.Event(), asyncio.Event()
        release_first, release_second = asyncio.Event(), asyncio.Event()
        first = asyncio.create_task(
            _hold_guard(harness, lineage_id=uuid4(), entered=first_entered, release=release_first)
        )
        async with asyncio.timeout(5):
            await first_entered.wait()
        second = asyncio.create_task(
            _hold_guard(
                harness,
                lineage_id=uuid4(),
                entered=second_entered,
                release=release_second,
                own_connection_first=True,
            )
        )
        await asyncio.sleep(_WAIT_SECONDS)

        # The waiter already owns an application connection, and the guard pool
        # is full: it must wait on the guard pool alone, never on the app pool.
        assert not second_entered.is_set()
        assert _checked_out(harness.app_engine) == _APP_POOL_SIZE

        release_first.set()
        async with asyncio.timeout(5):
            await second_entered.wait()
        release_second.set()
        await asyncio.gather(first, second)


async def test_guard_wait_is_bounded_by_the_pool_timeout(migrated_db: str) -> None:
    async with _harness(migrated_db, guard_timeout=0.3) as harness:
        entered, release = asyncio.Event(), asyncio.Event()
        holder = asyncio.create_task(
            _hold_guard(harness, lineage_id=uuid4(), entered=entered, release=release)
        )
        async with asyncio.timeout(5):
            await entered.wait()
        async with harness.sessions() as session:
            repository = harness.repository(session)
            with pytest.raises(PoolTimeoutError):
                async with repository.guard_document_payload(
                    user_id=uuid4(), document_lineage_id=uuid4()
                ):
                    pytest.fail("a full guard pool must not admit a second guard")
            # The failed wait leaves the application session usable.
            assert await session.scalar(text("SELECT 1")) == 1
        release.set()
        await holder
