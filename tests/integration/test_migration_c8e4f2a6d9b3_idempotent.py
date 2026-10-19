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

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer

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

_SchemaAssertion = Callable[[AsyncEngine], Awaitable[None]]


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


async def _with_engine(database_url: str, assertion: _SchemaAssertion) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await assertion(engine)
    finally:
        await engine.dispose()


def test_migration_c8e4f2a6d9b3_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id=_REVISION,
        schema_assertion=_assert_exam_guest_draft_handoffs_schema,
    )


def test_downgrade_drops_exam_guest_draft_handoffs_and_reupgrade_restores(
    alembic_config: Config, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_absent))

    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_schema))

    command.downgrade(alembic_config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_absent))

    command.upgrade(alembic_config, "head")
    asyncio.run(_with_engine(database_url, _assert_exam_guest_draft_handoffs_schema))
