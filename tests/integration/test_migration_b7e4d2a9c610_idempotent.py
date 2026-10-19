"""The queued import course key is nullable, bounded and migration-safe."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_import_course_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        columns = await connection.execute(
            text(
                """
                SELECT data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'exam_answer_key_enrichment_jobs'
                  AND column_name = 'workspace_course_key'
                """
            )
        )
        assert tuple(columns.one()) == ("character varying", 64, "YES")


def test_migration_b7e4d2a9c610_is_idempotent(empty_module_database: PooledDatabase) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="b7e4d2a9c610",
        schema_assertion=_assert_import_course_schema,
    )
