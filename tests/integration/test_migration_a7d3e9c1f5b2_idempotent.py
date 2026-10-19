"""Job diagnostics schema, existing-row backfill and downgrade coverage."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_diagnostics_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column = await connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'exam_answer_key_enrichment_jobs' "
                "AND column_name = 'diagnostics'"
            )
        )
        assert tuple(column.one()) == ("jsonb", "NO", "'[]'::jsonb")


def test_migration_a7d3e9c1f5b2_is_idempotent(empty_module_database: PooledDatabase) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="a7d3e9c1f5b2",
        schema_assertion=_assert_diagnostics_schema,
    )


async def _seed_existing_job(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO exam_answer_key_enrichment_jobs "
                    "(id, owner_user_id, source_kind, status, input_filename, source_docx, "
                    "workspace_lineage_id, workspace_document_revision) "
                    "VALUES (:id, :owner, 'docx_import', 'queued', 'quiz.docx', :docx, "
                    ":lineage, 1)"
                ),
                {
                    "id": uuid4(),
                    "owner": uuid4(),
                    "docx": b"temporary-docx",
                    "lineage": uuid4(),
                },
            )
    finally:
        await engine.dispose()


async def _assert_backfill(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        await _assert_diagnostics_schema(engine)
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT diagnostics FROM exam_answer_key_enrichment_jobs")
            )
            assert result.scalar_one() == []
    finally:
        await engine.dispose()


async def _assert_downgrade_state(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            column_count = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'exam_answer_key_enrichment_jobs' "
                    "AND column_name = 'diagnostics'"
                )
            )
            assert column_count == 0
            row_count = await connection.scalar(
                text("SELECT count(*) FROM exam_answer_key_enrichment_jobs")
            )
            assert row_count == 1
    finally:
        await engine.dispose()


def test_existing_job_gets_empty_array_and_downgrade_preserves_row(
    alembic_config: Config, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "e6a9c2f4b8d1")
    asyncio.run(_seed_existing_job(database_url))
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")
    asyncio.run(_assert_backfill(database_url))
    command.downgrade(alembic_config, "e6a9c2f4b8d1")
    asyncio.run(_assert_downgrade_state(database_url))
    command.upgrade(alembic_config, "head")
    asyncio.run(_assert_backfill(database_url))
