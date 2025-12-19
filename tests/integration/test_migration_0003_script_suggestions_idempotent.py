from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer


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


async def _script_suggestion_count(*, database_url: str) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await _count(engine, "SELECT COUNT(*) FROM script_suggestions")
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0003_script_suggestions_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        assert asyncio.run(_script_suggestion_count(database_url=database_url)) == 0

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        assert asyncio.run(_script_suggestion_count(database_url=database_url)) == 0
