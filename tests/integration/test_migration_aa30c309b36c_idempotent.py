"""Integration coverage for the exam import job conversion phase columns.

Purpose:
    Verify the `aa30c309b36c` Alembic revision remains idempotent: repeated
    upgrade cycles leave the nullable `conversion_phase` and
    `conversion_phase_started_at` columns present on the
    `exam_answer_key_enrichment_jobs` ledger.

Relationships:
    - Exercises `migrations/versions/aa30c309b36c_add_exam_job_conversion_phase.py`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

_REVISION_ID = "aa30c309b36c"


async def _assert_phase_columns(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'exam_answer_key_enrichment_jobs'
                  AND column_name IN ('conversion_phase', 'conversion_phase_started_at')
                ORDER BY column_name
                """
            )
        )
    assert [tuple(row) for row in rows.fetchall()] == [
        ("conversion_phase", "character varying", "YES"),
        ("conversion_phase_started_at", "timestamp with time zone", "YES"),
    ]


@pytest.mark.docker
def test_migration_aa30c309b36c_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_phase_columns,
    )
