from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT COUNT(*) FROM script_suggestion_decisions"))
        await conn.execute(
            text(
                "SELECT status, reviewed_by_user_id, reviewed_at, review_rationale, draft_tool_id "
                "FROM script_suggestions LIMIT 0"
            )
        )
        await conn.execute(text("SELECT is_published FROM tools LIMIT 0"))


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0004_suggestion_review_decisions_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0003_script_suggestions")
    command.upgrade(alembic_cfg, "0004_suggestion_review_decisions")
    command.upgrade(alembic_cfg, "0004_suggestion_review_decisions")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0003_script_suggestions")
    command.upgrade(alembic_cfg, "0004_suggestion_review_decisions")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
