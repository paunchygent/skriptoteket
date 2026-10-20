from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_versions' AND column_name = 'input_schema'"
            )
        )
        row = result.one_or_none()
        assert row is not None, "input_schema column should exist"
        data_type, is_nullable = row
        assert data_type == "jsonb", f"Expected jsonb, got {data_type}"
        # 0016 adds input_schema nullable; 0023_input_schema_not_null makes it NOT NULL.
        assert is_nullable == "YES", f"Expected nullable, got is_nullable={is_nullable}"


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0016_tool_versions_input_schema_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0015_usage_instructions")
    command.upgrade(alembic_cfg, "0016_tool_versions_input_schema")
    command.upgrade(alembic_cfg, "0016_tool_versions_input_schema")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0015_usage_instructions")
    command.upgrade(alembic_cfg, "0016_tool_versions_input_schema")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
