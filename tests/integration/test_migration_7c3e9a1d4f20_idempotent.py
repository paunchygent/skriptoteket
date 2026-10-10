"""Migration coverage for exam workspace document lineage on vault files."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_vault_document_lineage_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        columns = await connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'user_vault_files'
                ORDER BY ordinal_position
                """
            )
        )
        assert {row[0] for row in columns} >= {
            "id",
            "user_id",
            "document_lineage_id",
            "document_version",
        }
        indexes = await connection.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'user_vault_files'
                """
            )
        )
        assert {row[0] for row in indexes} >= {
            "ix_user_vault_files_document_lineage_id",
            "uq_user_vault_files_document_version",
        }


def test_migration_7c3e9a1d4f20_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id="7c3e9a1d4f20",
        schema_assertion=_assert_vault_document_lineage_schema,
    )
