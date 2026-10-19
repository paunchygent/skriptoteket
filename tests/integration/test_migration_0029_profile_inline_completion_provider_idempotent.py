from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _assert_inline_completion_provider_column_exists(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_profiles' "
                "AND column_name = 'inline_completion_provider'"
            )
        )
        assert result.scalar_one_or_none() == 16


async def _assert_inline_completion_provider_column_exists_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _assert_inline_completion_provider_column_exists(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0029_profile_inline_completion_provider_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "head")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(
        _assert_inline_completion_provider_column_exists_from_url(database_url=database_url)
    )

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    asyncio.run(
        _assert_inline_completion_provider_column_exists_from_url(database_url=database_url)
    )
