"""DOCX queue schema rerun and data-preserving downgrade coverage."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_docx_queue_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column = await connection.execute(
            text(
                "SELECT data_type, is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'exam_answer_key_enrichment_jobs' "
                "AND column_name = 'source_docx'"
            )
        )
        assert tuple(column.one()) == ("bytea", "YES")
        indexes = await connection.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'exam_answer_key_enrichment_jobs'"
            )
        )
        definitions: dict[str, str] = {row[0]: row[1] for row in indexes.all()}
        workspace = definitions["uq_exam_answer_key_enrichment_jobs_workspace_revision"]
        imported = definitions["uq_exam_answer_key_enrichment_jobs_docx_import_lineage"]
        assert "UNIQUE" in workspace and "UNIQUE" in imported
        assert "(workspace_lineage_id, workspace_document_revision)" in workspace
        assert "source_kind" in workspace and "'workspace'" in workspace
        assert "(workspace_lineage_id)" in imported
        assert "source_kind" in imported and "'docx_import'" in imported


def test_migration_e6a9c2f4b8d1_is_idempotent(postgres_container: PostgresContainer) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id="e6a9c2f4b8d1",
        schema_assertion=_assert_docx_queue_schema,
    )


async def _seed_coexisting_jobs(database_url: str) -> None:
    engine = create_async_engine(database_url)
    lineage_id, owner_id = uuid4(), uuid4()
    try:
        async with engine.begin() as connection:
            for source_kind in ("docx_import", "workspace"):
                await connection.execute(
                    text(
                        "INSERT INTO exam_answer_key_enrichment_jobs "
                        "(id, owner_user_id, source_kind, status, input_filename, source_docx, "
                        "workspace_lineage_id, workspace_document_revision) "
                        "VALUES (:id, :owner, :kind, 'queued', 'quiz.docx', :docx, :lineage, 1)"
                    ),
                    {
                        "id": uuid4(),
                        "owner": owner_id,
                        "kind": source_kind,
                        "docx": b"temporary-docx" if source_kind == "docx_import" else None,
                        "lineage": lineage_id,
                    },
                )
    finally:
        await engine.dispose()


async def _assert_downgrade_state(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            kinds = await connection.execute(
                text("SELECT source_kind FROM exam_answer_key_enrichment_jobs")
            )
            assert kinds.scalars().all() == ["workspace"]
            column_count = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'exam_answer_key_enrichment_jobs' "
                    "AND column_name = 'source_docx'"
                )
            )
            assert column_count == 0
            indexes = await connection.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename = 'exam_answer_key_enrichment_jobs'"
                )
            )
            definitions: dict[str, str] = {row[0]: row[1] for row in indexes.all()}
            assert "uq_exam_answer_key_enrichment_jobs_docx_import_lineage" not in definitions
            restored = definitions["uq_exam_answer_key_enrichment_jobs_workspace_revision"]
            assert "workspace_lineage_id IS NOT NULL" in restored
    finally:
        await engine.dispose()


def test_fresh_head_rerun_and_downgrade_delete_only_import_rows(
    alembic_config: Config, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")
    asyncio.run(_seed_coexisting_jobs(database_url))
    command.downgrade(alembic_config, "d4f8b2c6a9e1")
    asyncio.run(_assert_downgrade_state(database_url))
    command.upgrade(alembic_config, "head")

    async def assert_restored_schema() -> None:
        engine = create_async_engine(database_url)
        try:
            await _assert_docx_queue_schema(engine)
        finally:
            await engine.dispose()

    asyncio.run(assert_restored_schema())
