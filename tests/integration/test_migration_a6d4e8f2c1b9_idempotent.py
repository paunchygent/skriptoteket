"""Migration coverage for the durable public Exam Converter queue."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_public_job_queue_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        columns = await connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'public_exam_converter_jobs'
                ORDER BY ordinal_position
                """
            )
        )
        assert {row[0] for row in columns} >= {
            "id",
            "status",
            "requested_targets",
            "source_dxe",
            "locked_by",
            "locked_until",
            "expires_at",
        }


def test_migration_a6d4e8f2c1b9_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id="a6d4e8f2c1b9",
        schema_assertion=_assert_public_job_queue_schema,
    )
