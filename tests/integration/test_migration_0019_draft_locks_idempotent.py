from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

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
                "WHERE table_name = 'draft_locks'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["tool_id"] == ("uuid", "NO")
        assert columns["draft_head_id"] == ("uuid", "NO")
        assert columns["locked_by_user_id"] == ("uuid", "NO")
        assert columns["locked_at"] == ("timestamp with time zone", "NO")
        assert columns["expires_at"] == ("timestamp with time zone", "NO")
        assert columns["forced_by_user_id"] == ("uuid", "YES")

        user_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0019-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        tool_id = uuid4()
        draft_head_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO draft_locks "
                "(tool_id, draft_head_id, locked_by_user_id, expires_at, forced_by_user_id) "
                "VALUES "
                "(:tool_id, :draft_head_id, :locked_by_user_id, :expires_at, :forced_by_user_id)"
            ),
            {
                "tool_id": tool_id,
                "draft_head_id": draft_head_id,
                "locked_by_user_id": user_id,
                "expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
                "forced_by_user_id": None,
            },
        )

        result = await conn.execute(
            text(
                "SELECT locked_at, expires_at FROM draft_locks "
                "WHERE tool_id = :tool_id AND draft_head_id = :draft_head_id"
            ),
            {"tool_id": tool_id, "draft_head_id": draft_head_id},
        )
        (locked_at, expires_at) = result.one()
        assert locked_at is not None
        assert expires_at is not None


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0019_draft_locks_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
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
