"""Integration coverage for the exam answer-key enrichment migration.

Purpose:
    Verify the `b7d3f1a5c9e2` Alembic revision remains idempotent and leaves
    the token-lease, enrichment-job, and proposed-overlay tables with the
    expected schema after repeated upgrade cycles.

Relationships:
    - Exercises
      `migrations/versions/b7d3f1a5c9e2_add_exam_answer_key_enrichment_vertical.py`.
    - Counts as the rule-054 migration coverage for the answer-key vertical.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

_REVISION_ID = "b7d3f1a5c9e2"


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


async def _assert_answer_key_vertical_schema(engine: AsyncEngine) -> None:
    assert await _column_names(engine, "exam_answer_key_token_leases") == [
        "id",
        "utc_day",
        "job_id",
        "item_id",
        "provider_profile_id",
        "reserved_tokens",
        "actual_tokens",
        "state",
        "created_at",
        "updated_at",
    ]
    assert {
        "ix_exam_answer_key_token_leases_day",
        "ix_exam_answer_key_token_leases_job_id",
    } <= await _index_names(engine, "exam_answer_key_token_leases")

    assert await _column_names(engine, "exam_answer_key_enrichment_jobs") == [
        "id",
        "conversion_job_id",
        "owner_user_id",
        "status",
        "input_filename",
        "source_dxe",
        "attempts",
        "max_attempts",
        "available_at",
        "locked_by",
        "locked_until",
        "last_error",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    ]
    assert {
        "ix_exam_answer_key_enrichment_jobs_claim",
        "ix_exam_answer_key_enrichment_jobs_status",
        "uq_exam_answer_key_enrichment_jobs_conversion_job_id",
    } <= await _index_names(engine, "exam_answer_key_enrichment_jobs")

    assert await _column_names(engine, "exam_answer_key_proposed_overlays") == [
        "id",
        "enrichment_job_id",
        "conversion_job_id",
        "owner_user_id",
        "source_file_sha256",
        "source_ir_sha256",
        "provider_profile_id",
        "model",
        "overlay_json",
        "created_at",
    ]
    assert {
        "ix_exam_answer_key_proposed_overlays_conversion_job_id",
        "uq_exam_answer_key_proposed_overlays_enrichment_job_id",
    } <= await _index_names(engine, "exam_answer_key_proposed_overlays")


@pytest.mark.docker
def test_migration_b7d3f1a5c9e2_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_answer_key_vertical_schema,
    )
