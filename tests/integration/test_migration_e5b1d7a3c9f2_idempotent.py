"""Integration coverage for dropping the profile AI consent and provider preference.

Purpose:
    Verify the `e5b1d7a3c9f2` Alembic revision removes
    `user_profiles.allow_remote_fallback` and
    `user_profiles.inline_completion_provider`, that downgrade restores them as
    nullable columns with their original types, and that repeated upgrade
    cycles are idempotent.

Relationships:
    - Exercises
      `migrations/versions/e5b1d7a3c9f2_drop_profile_ai_consent_and_provider_preference.py`.
"""

from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import (
    SchemaAssertion,
    assert_revision_is_idempotent,
)

_REVISION_ID = "e5b1d7a3c9f2"
_PARENT_REVISION_ID = "9f3c7a1b4e02"
_DROPPED_COLUMNS = {"allow_remote_fallback", "inline_completion_provider"}


async def _profile_columns(engine: AsyncEngine) -> dict[str, tuple[str, str, int | None]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """
                SELECT column_name, is_nullable, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'user_profiles'
                """
            )
        )
    return {row[0]: (row[1], row[2], row[3]) for row in rows.fetchall()}


async def _assert_columns_dropped(engine: AsyncEngine) -> None:
    columns = await _profile_columns(engine)
    assert "user_id" in columns
    assert _DROPPED_COLUMNS.isdisjoint(columns)


async def _assert_columns_restored(engine: AsyncEngine) -> None:
    columns = await _profile_columns(engine)
    assert columns["allow_remote_fallback"] == ("YES", "boolean", None)
    assert columns["inline_completion_provider"] == ("YES", "character varying", 16)


async def _assert_from_url(*, database_url: str, assertion: SchemaAssertion) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await assertion(engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_e5b1d7a3c9f2_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_columns_dropped,
    )


@pytest.mark.docker
def test_migration_e5b1d7a3c9f2_downgrade_restores_nullable_columns(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)
    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, _REVISION_ID)
    asyncio.run(_assert_from_url(database_url=database_url, assertion=_assert_columns_dropped))

    command.downgrade(alembic_cfg, _PARENT_REVISION_ID)
    asyncio.run(_assert_from_url(database_url=database_url, assertion=_assert_columns_restored))

    # Re-upgrading after the downgrade drops the restored columns again, twice without error.
    command.upgrade(alembic_cfg, _REVISION_ID)
    command.upgrade(alembic_cfg, _REVISION_ID)
    asyncio.run(_assert_from_url(database_url=database_url, assertion=_assert_columns_dropped))
