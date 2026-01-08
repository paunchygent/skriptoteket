from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

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


def _column_map(rows: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {row[0]: (row[1], row[2]) for row in rows}


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_session_messages'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["id"] == ("uuid", "NO")
        assert columns["tool_session_id"] == ("uuid", "NO")
        assert columns["message_id"] == ("uuid", "NO")
        assert columns["role"] == ("character varying", "NO")
        assert columns["content"] == ("text", "NO")
        assert columns["meta"] == ("jsonb", "YES")
        assert columns["sequence"] == ("bigint", "NO")
        assert columns["created_at"] == ("timestamp with time zone", "NO")

        result = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'tool_session_messages' ORDER BY indexname"
            )
        )
        index_names = [row[0] for row in result.fetchall()]
        assert "ix_tool_session_messages_session_message_id" in index_names
        assert "ix_tool_session_messages_session_sequence" in index_names

        result = await conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'tool_session_messages'::regclass AND contype = 'u'"
            )
        )
        constraint_names = [row[0] for row in result.fetchall()]
        assert "uq_tool_session_messages_session_message_id" in constraint_names

        await conn.execute(text("SELECT COUNT(*) FROM tool_session_messages"))


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0024_tool_session_messages_is_idempotent(
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
