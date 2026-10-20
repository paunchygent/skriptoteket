"""Job conversion progress schema, existing-row null default and downgrade coverage."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_REVISION = "c4f8a2d6b9e1"
_PREVIOUS_REVISION = "e3b7a1c5d9f2"


async def _assert_progress_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column = await connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'exam_answer_key_enrichment_jobs' "
                "AND column_name = 'conversion_progress'"
            )
        )
        assert tuple(column.one()) == ("jsonb", "YES", None)


def test_migration_c4f8a2d6b9e1_is_idempotent(empty_module_database: PooledDatabase) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="c4f8a2d6b9e1",
        schema_assertion=_assert_progress_schema,
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


async def _assert_null_progress(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        await _assert_progress_schema(engine)
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT conversion_progress FROM exam_answer_key_enrichment_jobs")
            )
            assert result.scalar_one() is None
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
                    "AND column_name = 'conversion_progress'"
                )
            )
            assert column_count == 0
            row_count = await connection.scalar(
                text("SELECT count(*) FROM exam_answer_key_enrichment_jobs")
            )
            assert row_count == 1
    finally:
        await engine.dispose()


def test_existing_job_gets_null_progress_and_downgrade_preserves_row(
    fresh_database: PooledDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config_for(database_url=database_url)
    command.upgrade(config, _PREVIOUS_REVISION)
    asyncio.run(_seed_existing_job(database_url))
    command.upgrade(config, _REVISION)
    command.upgrade(config, _REVISION)
    asyncio.run(_assert_null_progress(database_url))
    command.downgrade(config, _PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade_state(database_url))
    command.upgrade(config, _REVISION)
    asyncio.run(_assert_null_progress(database_url))
