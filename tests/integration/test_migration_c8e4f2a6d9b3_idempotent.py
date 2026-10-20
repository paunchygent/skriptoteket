"""Schema and downgrade coverage for the exam guest draft handoff ledger.

Purpose:
    Verify the `c8e4f2a6d9b3` Alembic revision creates the
    `exam_guest_draft_handoffs` ledger with its composite primary key and the
    owner foreign key, and that downgrading removes it cleanly.

Relationships:
    - Exercises
      `migrations/versions/c8e4f2a6d9b3_add_exam_guest_draft_handoffs.py`.
    - Backs the sign-in guest-draft handoff (TASK-SKRIPT-41-02-02 P5).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent
from tests.integration.migration_schema_helpers import (
    column_map,
    index_names,
    table_names,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_REVISION = "c8e4f2a6d9b3"
_PARENT = "a1c2e3f4b5d6"
_TABLE = "exam_guest_draft_handoffs"

_T = TypeVar("_T")


async def _primary_key_columns(engine: AsyncEngine) -> list[str]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT kcu.column_name "
                "FROM information_schema.table_constraints AS tc "
                "JOIN information_schema.key_column_usage AS kcu "
                "  ON kcu.constraint_name = tc.constraint_name "
                " AND kcu.constraint_schema = tc.constraint_schema "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = :table "
                "ORDER BY kcu.ordinal_position"
            ),
            {"table": _TABLE},
        )
        return [row[0] for row in result.fetchall()]


async def _foreign_keys(engine: AsyncEngine) -> set[tuple[str, str, str]]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT kcu.column_name, "
                "       ccu.table_name AS foreign_table, "
                "       ccu.column_name AS foreign_column "
                "FROM information_schema.table_constraints AS tc "
                "JOIN information_schema.key_column_usage AS kcu "
                "  ON kcu.constraint_name = tc.constraint_name "
                " AND kcu.constraint_schema = tc.constraint_schema "
                "JOIN information_schema.constraint_column_usage AS ccu "
                "  ON ccu.constraint_name = tc.constraint_name "
                " AND ccu.constraint_schema = tc.constraint_schema "
                "WHERE tc.constraint_type = 'FOREIGN KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = :table"
            ),
            {"table": _TABLE},
        )
        return {(row[0], row[1], row[2]) for row in result.fetchall()}


async def _assert_exam_guest_draft_handoffs_schema(engine: AsyncEngine) -> None:
    assert _TABLE in await table_names(engine)

    columns = await column_map(engine, _TABLE)
    assert set(columns) == {"owner_user_id", "draft_id", "lineage_id", "created_at"}
    assert {name: column["is_nullable"] for name, column in columns.items()} == {
        "owner_user_id": "NO",
        "draft_id": "NO",
        "lineage_id": "NO",
        "created_at": "NO",
    }

    assert await _primary_key_columns(engine) == ["owner_user_id", "draft_id"]
    assert await _foreign_keys(engine) == {("owner_user_id", "users", "id")}

    assert f"{_TABLE}_pkey" in await index_names(engine, _TABLE)


async def _assert_exam_guest_draft_handoffs_absent(engine: AsyncEngine) -> None:
    assert _TABLE not in await table_names(engine)
    assert await index_names(engine, _TABLE) == set()


async def _seed_owner_user(engine: AsyncEngine) -> UUID:
    owner_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO users (id, email, role, auth_provider) "
                "VALUES (:id, 'guest-owner@example.com', 'guest', 'local')"
            ),
            {"id": owner_id},
        )
    return owner_id


async def _seed_handoff(engine: AsyncEngine, owner_id: UUID) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO exam_guest_draft_handoffs "
                "(owner_user_id, draft_id, lineage_id, created_at) "
                "VALUES (:owner, :draft, :lineage, now())"
            ),
            {"owner": owner_id, "draft": uuid4(), "lineage": uuid4()},
        )


async def _handoff_count(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        count = await connection.scalar(text("SELECT count(*) FROM exam_guest_draft_handoffs"))
        assert isinstance(count, int)
        return count


async def _with_engine(database_url: str, action: Callable[[AsyncEngine], Awaitable[_T]]) -> _T:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await action(engine)
    finally:
        await engine.dispose()


def test_migration_c8e4f2a6d9b3_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION,
        schema_assertion=_assert_exam_guest_draft_handoffs_schema,
    )


def test_downgrade_drops_exam_guest_draft_handoffs_and_reupgrade_restores(
    fresh_database: PooledDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config_for(database_url=database_url)
    command.upgrade(config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_absent))
    owner_id = asyncio.run(_with_engine(database_url, _seed_owner_user))

    async def _seed_owner_handoff(engine: AsyncEngine) -> None:
        await _seed_handoff(engine, owner_id)

    command.upgrade(config, _REVISION)
    command.upgrade(config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_schema))
    asyncio.run(_with_engine(database_url, _seed_owner_handoff))
    assert asyncio.run(_with_engine(database_url, _handoff_count)) == 1

    command.downgrade(config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_absent))

    command.upgrade(config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_schema))
    assert asyncio.run(_with_engine(database_url, _handoff_count)) == 0
    asyncio.run(_with_engine(database_url, _seed_owner_handoff))
    assert asyncio.run(_with_engine(database_url, _handoff_count)) == 1
