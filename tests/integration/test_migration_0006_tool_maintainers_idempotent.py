from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT COUNT(*) FROM tool_maintainers"))
        await conn.execute(text("SELECT tool_id, user_id FROM tool_maintainers LIMIT 0"))


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0006_tool_maintainers_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, fresh_database: PooledDatabase
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0005_tool_versions")
    command.upgrade(alembic_cfg, "0006_tool_maintainers")
    command.upgrade(alembic_cfg, "0006_tool_maintainers")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0005_tool_versions")
    command.upgrade(alembic_cfg, "0006_tool_maintainers")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
