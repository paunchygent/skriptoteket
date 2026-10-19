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


async def _taxonomy_counts(*, database_url: str) -> tuple[int, int, int]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        professions = await _count(engine, "SELECT COUNT(*) FROM professions")
        categories = await _count(engine, "SELECT COUNT(*) FROM categories")
        profession_categories = await _count(engine, "SELECT COUNT(*) FROM profession_categories")
        return professions, categories, profession_categories
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0002_catalog_taxonomy_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, fresh_database: PooledDatabase
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "head")
    command.upgrade(alembic_cfg, "head")

    professions, categories, profession_categories = asyncio.run(
        _taxonomy_counts(database_url=database_url)
    )
    assert professions == 5
    assert categories == 4
    assert profession_categories == 20

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    professions, categories, profession_categories = asyncio.run(
        _taxonomy_counts(database_url=database_url)
    )
    assert professions == 5
    assert categories == 4
    assert profession_categories == 20
