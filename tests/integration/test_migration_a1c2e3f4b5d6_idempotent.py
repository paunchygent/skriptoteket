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
from typing import TypeVar

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
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


async def _seed_request_window(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO public_request_windows "
                "(bucket, caller_key, window_start, request_count) "
                "VALUES ('public-guest', 'test-key', now(), 1)"
            )
        )


async def _request_window_count(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        count = await connection.scalar(text("SELECT count(*) FROM public_request_windows"))
        assert isinstance(count, int)
        return count


async def _with_engine(database_url: str, action: Callable[[AsyncEngine], Awaitable[_T]]) -> _T:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await action(engine)
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
    fresh_database: PooledDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config_for(database_url=database_url)
    command.upgrade(config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_absent))

    command.upgrade(config, _REVISION)
    command.upgrade(config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_schema))
    asyncio.run(_with_engine(database_url, _seed_request_window))
    assert asyncio.run(_with_engine(database_url, _request_window_count)) == 1

    command.downgrade(config, _PARENT)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_absent))

    command.upgrade(config, _REVISION)
    asyncio.run(_with_engine(database_url, _assert_public_request_windows_schema))
    assert asyncio.run(_with_engine(database_url, _request_window_count)) == 0
    asyncio.run(_with_engine(database_url, _seed_request_window))
    assert asyncio.run(_with_engine(database_url, _request_window_count)) == 1
