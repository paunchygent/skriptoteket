from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _count(engine: AsyncEngine, sql: str) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(text(sql))
        return int(result.scalar_one())


async def _script_suggestion_count(*, database_url: str) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await _count(engine, "SELECT COUNT(*) FROM script_suggestions")
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0003_script_suggestions_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, fresh_database: PooledDatabase
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "head")
    command.upgrade(alembic_cfg, "head")

    assert asyncio.run(_script_suggestion_count(database_url=database_url)) == 0

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    assert asyncio.run(_script_suggestion_count(database_url=database_url)) == 0
