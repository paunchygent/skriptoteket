"""Tool version bundle files schema and idempotency coverage."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_bundle_files_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column = await connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'tool_versions' AND column_name = 'bundle_files'"
            )
        )
        assert tuple(column.one()) == ("jsonb", "NO", "'{}'::jsonb")


def test_migration_d4be51baf417_is_idempotent(postgres_container: PostgresContainer) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id="d4be51baf417",
        schema_assertion=_assert_bundle_files_schema,
    )
