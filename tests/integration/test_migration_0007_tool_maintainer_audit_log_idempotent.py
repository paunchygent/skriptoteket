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


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        # Verify table exists with all expected columns
        await conn.execute(text("SELECT COUNT(*) FROM tool_maintainer_audit_log"))
        await conn.execute(
            text(
                "SELECT id, tool_id, user_id, action, performed_by_user_id, "
                "performed_at, reason FROM tool_maintainer_audit_log LIMIT 0"
            )
        )
        # Verify indexes exist
        result = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'tool_maintainer_audit_log' ORDER BY indexname"
            )
        )
        index_names = [row[0] for row in result.fetchall()]
        assert "ix_tool_maintainer_audit_log_tool_id" in index_names
        assert "ix_tool_maintainer_audit_log_user_id" in index_names


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0007_tool_maintainer_audit_log_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))
