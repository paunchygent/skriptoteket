from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT COUNT(*) FROM tool_sessions"))
        await conn.execute(
            text(
                "SELECT id, tool_id, user_id, context, state, state_rev, created_at, updated_at "
                "FROM tool_sessions LIMIT 0"
            )
        )


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0009_tool_sessions_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0008_tool_runs_ui_payload")
    command.upgrade(alembic_cfg, "0009_tool_sessions")
    command.upgrade(alembic_cfg, "0009_tool_sessions")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0008_tool_runs_ui_payload")
    command.upgrade(alembic_cfg, "0009_tool_sessions")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
