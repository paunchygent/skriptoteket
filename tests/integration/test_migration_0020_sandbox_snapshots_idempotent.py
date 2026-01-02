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
                "WHERE table_name = 'sandbox_snapshots'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["id"] == ("uuid", "NO")
        assert columns["tool_id"] == ("uuid", "NO")
        assert columns["draft_head_id"] == ("uuid", "NO")
        assert columns["created_by_user_id"] == ("uuid", "NO")
        assert columns["entrypoint"] == ("character varying", "NO")
        assert columns["source_code"] == ("text", "NO")
        assert columns["settings_schema"] == ("jsonb", "YES")
        assert columns["input_schema"] == ("jsonb", "NO")
        assert columns["usage_instructions"] == ("text", "YES")
        assert columns["payload_bytes"] == ("bigint", "NO")
        assert columns["created_at"] == ("timestamp with time zone", "NO")
        assert columns["expires_at"] == ("timestamp with time zone", "NO")

        result = await conn.execute(
            text(
                "SELECT data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_runs' AND column_name = 'snapshot_id'"
            )
        )
        row = result.one_or_none()
        assert row is not None, "snapshot_id column should exist"
        data_type, is_nullable = row
        assert data_type == "uuid"
        assert is_nullable == "YES"

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
                "email": f"migration-0020-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        tool_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO tools "
                "(id, owner_user_id, slug, title) "
                "VALUES "
                "(:id, :owner_user_id, :slug, :title)"
            ),
            {
                "id": tool_id,
                "owner_user_id": user_id,
                "slug": f"migration-0020-{tool_id.hex[:8]}",
                "title": "Migration 0020 Tool",
            },
        )

        version_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO tool_versions "
                "(id, tool_id, version_number, state, source_code, entrypoint, content_hash, "
                "created_by_user_id) "
                "VALUES "
                "(:id, :tool_id, :version_number, :state, :source_code, :entrypoint, "
                ":content_hash, :created_by_user_id)"
            ),
            {
                "id": version_id,
                "tool_id": tool_id,
                "version_number": 1,
                "state": "draft",
                "source_code": "print('hi')",
                "entrypoint": "main.py",
                "content_hash": "0" * 64,
                "created_by_user_id": user_id,
            },
        )

        snapshot_id = uuid4()
        expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        await conn.execute(
            text(
                "INSERT INTO sandbox_snapshots "
                "(id, tool_id, draft_head_id, created_by_user_id, entrypoint, source_code, "
                "settings_schema, input_schema, usage_instructions, payload_bytes, expires_at) "
                "VALUES "
                "(:id, :tool_id, :draft_head_id, :created_by_user_id, :entrypoint, :source_code, "
                ":settings_schema, :input_schema, :usage_instructions, :payload_bytes, :expires_at)"
            ),
            {
                "id": snapshot_id,
                "tool_id": tool_id,
                "draft_head_id": version_id,
                "created_by_user_id": user_id,
                "entrypoint": "main.py",
                "source_code": "print('hi')",
                "settings_schema": None,
                "input_schema": "[]",
                "usage_instructions": None,
                "payload_bytes": 123,
                "expires_at": expires_at,
            },
        )

        result = await conn.execute(
            text(
                "SELECT created_at, expires_at, payload_bytes FROM sandbox_snapshots WHERE id = :id"
            ),
            {"id": snapshot_id},
        )
        created_at, expires_at_db, payload_bytes = result.one()
        assert created_at is not None
        assert expires_at_db == expires_at
        assert payload_bytes == 123


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0020_sandbox_snapshots_is_idempotent(
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
