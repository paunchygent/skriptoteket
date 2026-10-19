"""Sandbox snapshot bundle files schema and idempotency coverage."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_bundle_files_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column = await connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'sandbox_snapshots' AND column_name = 'bundle_files'"
            )
        )
        assert tuple(column.one()) == ("jsonb", "NO", "'{}'::jsonb")


def test_migration_e3b7a1c5d9f2_is_idempotent(empty_module_database: PooledDatabase) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="e3b7a1c5d9f2",
        schema_assertion=_assert_bundle_files_schema,
    )
