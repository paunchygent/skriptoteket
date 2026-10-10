"""Migration coverage for the workspace-generalized answer-key enrichment lane."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_enrichment_workspace_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        job_columns = await connection.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'exam_answer_key_enrichment_jobs'
                """
            )
        )
        columns = {row[0]: row[1] for row in job_columns}
        assert "source_kind" in columns
        assert "workspace_lineage_id" in columns
        assert "workspace_document_revision" in columns
        assert columns.get("conversion_job_id") == "YES"
        assert columns.get("source_dxe") == "YES"

        indexes = await connection.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'exam_answer_key_enrichment_jobs'
                """
            )
        )
        assert "uq_exam_answer_key_enrichment_jobs_workspace_revision" in {
            row[0] for row in indexes
        }

        overlay_columns = await connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'exam_answer_key_proposed_overlays'
                """
            )
        )
        assert {row[0] for row in overlay_columns} >= {
            "workspace_lineage_id",
            "workspace_document_revision",
        }


def test_migration_d4f8b2c6a9e1_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id="d4f8b2c6a9e1",
        schema_assertion=_assert_enrichment_workspace_schema,
    )
