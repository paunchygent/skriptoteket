"""Schema and downgrade coverage for the shared public request window table.

Purpose:
    Verify the `a1c2e3f4b5d6` Alembic revision creates the
    `public_request_windows` counter table with its composite primary key and
    `window_start` index, and that downgrading removes it cleanly.

Relationships:
    - Exercises
      `migrations/versions/a1c2e3f4b5d6_add_public_request_windows.py`.
    - Backs the DB limiter used by public guest routes (TASK-SKRIPT-41-02-02).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent
from tests.integration.migration_schema_helpers import (
    column_map,
    index_definitions,
    index_names,
    table_names,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_REVISION = "a1c2e3f4b5d6"
_PARENT = "e8a3c5f1b7d2"
_TABLE = "public_request_windows"
_INDEX = "ix_public_request_windows_window_start"

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


async def _assert_public_request_windows_schema(engine: AsyncEngine) -> None:
    assert _TABLE in await table_names(engine)

    columns = await column_map(engine, _TABLE)
    assert set(columns) == {"bucket", "caller_key", "window_start", "request_count"}
    assert {name: column["is_nullable"] for name, column in columns.items()} == {
        "bucket": "NO",
        "caller_key": "NO",
        "window_start": "NO",
        "request_count": "NO",
    }

    assert await _primary_key_columns(engine) == ["bucket", "caller_key", "window_start"]

    indexes = await index_names(engine, _TABLE)
    assert {f"{_TABLE}_pkey", _INDEX} <= indexes
    definitions = await index_definitions(engine, _TABLE)
    assert definitions[_INDEX].endswith(" btree (window_start)")
    assert "UNIQUE" not in definitions[_INDEX]


async def _assert_public_request_windows_absent(engine: AsyncEngine) -> None:
    assert _TABLE not in await table_names(engine)
    assert await index_names(engine, _TABLE) == set()
    assert await index_definitions(engine, _TABLE) == {}


async def _with_engine(database_url: str, assertion: _SchemaAssertion) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await assertion(engine)
    finally:
        await engine.dispose()


def test_migration_a1c2e3f4b5d6_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION,
        schema_assertion=_assert_public_request_windows_schema,
    )


def test_downgrade_drops_public_request_windows_and_reupgrade_restores(
    alembic_config: Config, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_absent))

    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_schema))

    command.downgrade(alembic_config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_absent))

    command.upgrade(alembic_config, "head")
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_schema))
