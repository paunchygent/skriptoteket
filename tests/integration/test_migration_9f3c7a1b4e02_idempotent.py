"""Integration coverage for dropping the answer-key token lease.

Purpose:
    Verify the `9f3c7a1b4e02` Alembic revision remains idempotent: repeated
    upgrade cycles leave the `exam_answer_key_token_leases` table (and its
    indexes) absent and the `ai_limit` column present on the
    `exam_answer_key_enrichment_jobs` ledger.

Relationships:
    - Exercises
      `migrations/versions/9f3c7a1b4e02_remove_answer_key_token_lease_add_door_limit.py`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

_REVISION_ID = "9f3c7a1b4e02"


async def _table_exists(engine: AsyncEngine, table_name: str) -> bool:
    async with engine.connect() as conn:
        exists = await conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        )
    return bool(exists.scalar_one())


async def _column_names(engine: AsyncEngine, table_name: str) -> list[str]:
    async with engine.connect() as conn:
        columns = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                ORDER BY ordinal_position
                """
            ),
            {"table_name": table_name},
        )
    return [row[0] for row in columns.fetchall()]


async def _index_names(engine: AsyncEngine, table_name: str) -> set[str]:
    async with engine.connect() as conn:
        indexes = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = :table_name
                """
            ),
            {"table_name": table_name},
        )
    return {row[0] for row in indexes.fetchall()}


async def _assert_lease_removed_schema(engine: AsyncEngine) -> None:
    assert not await _table_exists(engine, "exam_answer_key_token_leases")
    assert "ai_limit" in await _column_names(engine, "exam_answer_key_enrichment_jobs")


@pytest.mark.docker
def test_migration_9f3c7a1b4e02_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_lease_removed_schema,
    )
