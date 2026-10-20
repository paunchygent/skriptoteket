"""Alembic coverage for dropping retired browser-auth sessions.

Purpose:
    Prove PR-0253 removes the `sessions` table cleanly and that downgrade
    recreates only an empty legacy table shape for recovery.

Relationships:
    - Covers migration `c1d2e3f4a5b6`.
    - Keeps `tool_sessions` out of scope because tool execution state remains
      first-class app data.
"""

from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _table_names(*, engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in result.fetchall()}


async def _assert_sessions_absent(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        tables = await _table_names(engine=engine)
        assert "sessions" not in tables
        assert "tool_sessions" in tables
    finally:
        await engine.dispose()


async def _assert_sessions_downgrade_shape(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'sessions'
                    """
                )
            )
            assert {
                "id",
                "user_id",
                "csrf_token",
                "allow_remote_fallback",
                "inline_completion_provider",
                "created_at",
                "expires_at",
                "revoked_at",
            }.issubset({row[0] for row in rows.fetchall()})
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_c1d2e3f4a5b6_drops_browser_auth_sessions(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0f4c2d7a9b1e")
    command.upgrade(alembic_cfg, "c1d2e3f4a5b6")
    command.upgrade(alembic_cfg, "c1d2e3f4a5b6")
    asyncio.run(_assert_sessions_absent(database_url=database_url))

    command.downgrade(alembic_cfg, "0f4c2d7a9b1e")
    asyncio.run(_assert_sessions_downgrade_shape(database_url=database_url))

    command.upgrade(alembic_cfg, "c1d2e3f4a5b6")
    asyncio.run(_assert_sessions_absent(database_url=database_url))
