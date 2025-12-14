from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]


def _to_async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+"):
        prefix, rest = url.split("://", 1)
        base = prefix.split("+", 1)[0]
        return f"{base}+asyncpg://{rest}"
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unsupported database url scheme: {url}")


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


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
def test_migration_0002_catalog_taxonomy_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

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
