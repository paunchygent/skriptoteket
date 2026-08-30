"""Integration coverage for native Exam Converter idempotency identities."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

_REVISION_ID = "c8e4f2a6d9b1"


async def _assert_native_idempotency_schema(engine: AsyncEngine) -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    submission_key = f"submission-{uuid4()}"

    async with engine.begin() as conn:
        columns = await conn.execute(
            text(
                """
                SELECT table_name, column_name, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (table_name, column_name) IN (
                    ('conversion_hub_jobs', 'submission_idempotency_key'),
                    ('exam_answer_key_enrichment_jobs', 'retry_identity')
                  )
                ORDER BY table_name
                """
            )
        )
        assert columns.fetchall() == [
            ("conversion_hub_jobs", "submission_idempotency_key", 128, "YES"),
            ("exam_answer_key_enrichment_jobs", "retry_identity", 255, "YES"),
        ]

        index = await conn.execute(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'conversion_hub_jobs'
                  AND indexname = 'uq_conversion_hub_jobs_owner_submission_key'
                """
            )
        )
        index_definition = index.scalar_one()
        assert "UNIQUE INDEX" in index_definition
        assert "(owner_user_id, submission_idempotency_key)" in index_definition
        assert "WHERE (submission_idempotency_key IS NOT NULL)" in index_definition

        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, role, auth_provider)
                VALUES
                  (:owner_id, :owner_email, 'user', 'local'),
                  (:other_owner_id, :other_owner_email, 'user', 'local')
                """
            ),
            {
                "owner_id": owner_id,
                "owner_email": f"{owner_id}@example.test",
                "other_owner_id": other_owner_id,
                "other_owner_email": f"{other_owner_id}@example.test",
            },
        )
        for job_id, job_owner_id in ((uuid4(), owner_id), (uuid4(), other_owner_id)):
            await conn.execute(
                text(
                    """
                    INSERT INTO conversion_hub_jobs (
                      id, owner_user_id, input_filename, source_format,
                      output_format, status, submission_idempotency_key
                    ) VALUES (
                      :id, :owner_user_id, 'exam.dxe', 'dxe',
                      'examnet', 'queued', :submission_key
                    )
                    """
                ),
                {
                    "id": job_id,
                    "owner_user_id": job_owner_id,
                    "submission_key": submission_key,
                },
            )

    async with engine.connect() as conn:
        transaction = await conn.begin()
        with pytest.raises(IntegrityError):
            await conn.execute(
                text(
                    """
                    INSERT INTO conversion_hub_jobs (
                      id, owner_user_id, input_filename, source_format,
                      output_format, status, submission_idempotency_key
                    ) VALUES (
                      :id, :owner_user_id, 'duplicate.dxe', 'dxe',
                      'examnet', 'queued', :submission_key
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "owner_user_id": owner_id,
                    "submission_key": submission_key,
                },
            )
        await transaction.rollback()

    conversion_job_id = uuid4()
    retry_identity = f"retry-{uuid4()}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO conversion_hub_jobs (
                  id, owner_user_id, input_filename, source_format, output_format, status
                ) VALUES (:id, :owner_user_id, 'retry.dxe', 'dxe', 'examnet', 'queued')
                """
            ),
            {"id": conversion_job_id, "owner_user_id": owner_id},
        )
        enrichment_job_id = uuid4()
        await conn.execute(
            text(
                """
                INSERT INTO exam_answer_key_enrichment_jobs (
                  id, conversion_job_id, owner_user_id, status,
                  input_filename, source_dxe, retry_identity
                ) VALUES (
                  :id, :conversion_job_id, :owner_user_id, 'queued',
                  'retry.dxe', :source_dxe, :retry_identity
                )
                """
            ),
            {
                "id": enrichment_job_id,
                "conversion_job_id": conversion_job_id,
                "owner_user_id": owner_id,
                "source_dxe": b"dxe",
                "retry_identity": retry_identity,
            },
        )
        stored_retry_identity = await conn.execute(
            text("SELECT retry_identity FROM exam_answer_key_enrichment_jobs WHERE id = :id"),
            {"id": enrichment_job_id},
        )
        assert stored_retry_identity.scalar_one() == retry_identity


@pytest.mark.docker
def test_migration_c8e4f2a6d9b1_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_native_idempotency_schema,
    )
