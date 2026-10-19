"""Integration tests for the PostgreSQL public request-window limiter.

Purpose:
    Prove the shared hourly counter semantics against real Postgres: an atomic
    conditional increment that refuses at the limit without changing the stored
    count, independent buckets and windows, a non-positive limit that writes
    nothing, survival across a freshly built engine, and window pruning.

Relationships:
    - Exercises ``PostgreSQLPublicRequestWindowRepository`` under the migrated
      schema.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skriptoteket.infrastructure.db.models.public_request_window import (
    PublicRequestWindowModel,
)
from skriptoteket.infrastructure.repositories.public_request_windows import (
    PostgreSQLPublicRequestWindowRepository,
)
from skriptoteket.protocols.public_request_limits import PublicRequestBucket

pytestmark = pytest.mark.asyncio(loop_scope="module")

_WINDOW = datetime(2026, 10, 18, 15, 0, tzinfo=UTC)
_LATER_WINDOW = datetime(2026, 10, 18, 17, 0, tzinfo=UTC)
_CALLER = "a" * 64


def _repository(session: AsyncSession) -> PostgreSQLPublicRequestWindowRepository:
    return PostgreSQLPublicRequestWindowRepository(session)


async def _stored_count(
    session: AsyncSession,
    *,
    bucket: PublicRequestBucket,
    caller_key: str,
    window_start: datetime,
) -> int | None:
    result = await session.execute(
        select(PublicRequestWindowModel.request_count).where(
            PublicRequestWindowModel.bucket == bucket.value,
            PublicRequestWindowModel.caller_key == caller_key,
            PublicRequestWindowModel.window_start == window_start,
        )
    )
    count = result.scalar_one_or_none()
    return int(count) if count is not None else None


async def test_increments_to_the_limit_then_refuses_without_changing_the_count(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session)

    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=2,
        )
        == 1
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=2,
        )
        == 2
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=2,
        )
        is None
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=2,
        )
        is None
    )
    assert (
        await _stored_count(
            db_session,
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
        )
        == 2
    )


async def test_buckets_and_windows_count_independently(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session)

    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=10,
        )
        == 1
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_EXPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=10,
        )
        == 1
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_LATER_WINDOW,
            limit=10,
        )
        == 1
    )
    assert (
        await _stored_count(
            db_session,
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
        )
        == 1
    )


async def test_non_positive_limit_refuses_and_inserts_nothing(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session)

    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_EDIT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=0,
        )
        is None
    )
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_EDIT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=-5,
        )
        is None
    )
    assert (
        await _stored_count(
            db_session,
            bucket=PublicRequestBucket.GUEST_EDIT,
            caller_key=_CALLER,
            window_start=_WINDOW,
        )
        is None
    )


async def test_count_survives_a_fresh_engine_and_session_factory(
    db_session: AsyncSession, database_url: str
) -> None:
    repository = _repository(db_session)
    assert (
        await repository.try_increment(
            bucket=PublicRequestBucket.GUEST_EXPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
            limit=5,
        )
        == 1
    )
    await db_session.commit()

    fresh_engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        fresh_factory = async_sessionmaker(
            fresh_engine, expire_on_commit=False, class_=AsyncSession
        )
        async with fresh_factory() as fresh_session:
            assert (
                await _repository(fresh_session).try_increment(
                    bucket=PublicRequestBucket.GUEST_EXPORT,
                    caller_key=_CALLER,
                    window_start=_WINDOW,
                    limit=5,
                )
                == 2
            )
    finally:
        await fresh_engine.dispose()


async def test_delete_windows_before_removes_only_older_windows(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session)
    await repository.try_increment(
        bucket=PublicRequestBucket.GUEST_IMPORT,
        caller_key=_CALLER,
        window_start=_WINDOW,
        limit=5,
    )
    await repository.try_increment(
        bucket=PublicRequestBucket.GUEST_IMPORT,
        caller_key=_CALLER,
        window_start=_LATER_WINDOW,
        limit=5,
    )

    await repository.delete_windows_before(cutoff=_WINDOW + timedelta(hours=1))

    assert (
        await _stored_count(
            db_session,
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_WINDOW,
        )
        is None
    )
    assert (
        await _stored_count(
            db_session,
            bucket=PublicRequestBucket.GUEST_IMPORT,
            caller_key=_CALLER,
            window_start=_LATER_WINDOW,
        )
        == 1
    )
