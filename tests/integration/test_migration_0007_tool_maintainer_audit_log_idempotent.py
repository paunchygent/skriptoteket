from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


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
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "head")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
