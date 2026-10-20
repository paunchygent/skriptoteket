from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'alembic_version' AND column_name = 'version_num'"
            )
        )
        data_type, max_length = result.one()
        assert data_type == "character varying"
        assert max_length == 64


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0014_alembic_varchar64_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0013_user_profiles_and_security")
    command.upgrade(alembic_cfg, "0014_alembic_varchar64")
    command.upgrade(alembic_cfg, "0014_alembic_varchar64")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0013_user_profiles_and_security")
    command.upgrade(alembic_cfg, "0014_alembic_varchar64")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
