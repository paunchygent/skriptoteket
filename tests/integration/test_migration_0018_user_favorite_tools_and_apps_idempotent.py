from __future__ import annotations

import asyncio
from typing import cast
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


def _column_map(rows: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {row[0]: (row[1], row[2]) for row in rows}


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_favorite_tools'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["user_id"] == ("uuid", "NO")
        assert columns["tool_id"] == ("uuid", "NO")
        assert columns["created_at"] == ("timestamp with time zone", "NO")

        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_favorite_apps'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["user_id"] == ("uuid", "NO")
        assert columns["app_id"] == ("character varying", "NO")
        assert columns["created_at"] == ("timestamp with time zone", "NO")

        user_id = uuid4()
        tool_id = uuid4()

        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0018-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        await conn.execute(
            text(
                "INSERT INTO tools "
                "(id, owner_user_id, slug, title, summary) "
                "VALUES "
                "(:id, :owner_user_id, :slug, :title, :summary)"
            ),
            {
                "id": tool_id,
                "owner_user_id": user_id,
                "slug": f"migration-0018-{tool_id.hex[:8]}",
                "title": "Favorite Migration Tool",
                "summary": None,
            },
        )

        await conn.execute(
            text("INSERT INTO user_favorite_tools (user_id, tool_id) VALUES (:user_id, :tool_id)"),
            {"user_id": user_id, "tool_id": tool_id},
        )
        await conn.execute(
            text("INSERT INTO user_favorite_apps (user_id, app_id) VALUES (:user_id, :app_id)"),
            {"user_id": user_id, "app_id": "demo.counter"},
        )

        result = await conn.execute(
            text(
                "SELECT created_at FROM user_favorite_tools "
                "WHERE user_id = :user_id AND tool_id = :tool_id"
            ),
            {"user_id": user_id, "tool_id": tool_id},
        )
        (tool_created_at,) = result.one()
        assert tool_created_at is not None

        result = await conn.execute(
            text(
                "SELECT created_at FROM user_favorite_apps "
                "WHERE user_id = :user_id AND app_id = :app_id"
            ),
            {"user_id": user_id, "app_id": "demo.counter"},
        )
        (app_created_at,) = result.one()
        assert app_created_at is not None


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0018_user_favorite_tools_and_apps_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0017_tool_runs_input_values")
    command.upgrade(alembic_cfg, "0018_user_favorite_tools_and_apps")
    command.upgrade(alembic_cfg, "0018_user_favorite_tools_and_apps")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0017_tool_runs_input_values")
    command.upgrade(alembic_cfg, "0018_user_favorite_tools_and_apps")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
