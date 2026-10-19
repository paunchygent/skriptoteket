from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _assert_session_context_column(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_runs' AND column_name = 'session_context'"
            )
        )
        row = result.one()
        assert row.is_nullable == "NO"
        assert row.column_default is not None
        assert "default" in str(row.column_default)


async def _assert_session_context_column_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _assert_session_context_column(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0031_tool_runs_session_context_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "head")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(_assert_session_context_column_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(_assert_session_context_column_from_url(database_url=database_url))
