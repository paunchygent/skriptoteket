"""Integration coverage for the workspace suggestion job lookup index migration.

Purpose:
    Verify the `a3e7c9d1f4b6` Alembic revision (TASK-SKRIPT-39-04-09)
    replaces the unique workspace revision index with a non-unique lookup
    index, so one saved version can carry several suggestion jobs, and leaves
    every existing job row as it was.

Relationships:
    - Exercises
      `migrations/versions/a3e7c9d1f4b6_index_workspace_suggestion_jobs_by_saved_version.py`.
"""

from __future__ import annotations

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from tests.fixtures.database_fixtures import _to_async_database_url
from tests.integration.migration_idempotency_support import _alembic_config, _reset_public_schema

_REVISION_ID = "a3e7c9d1f4b6"
_PARENT_REVISION = "f5c2a8d3e7b4"
_LINEAGE = uuid4()


async def _insert_workspace_job(database_url: str, revision: int | None) -> UUID:
    job_id = uuid4()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO exam_answer_key_enrichment_jobs
                        (id, source_kind, owner_user_id, status, input_filename,
                         workspace_lineage_id, workspace_document_revision,
                         workspace_request_json)
                    VALUES (:id, 'workspace', :owner, 'succeeded', 'prov',
                            :lineage, :revision, '{"views": []}'::jsonb)
                    """
                ),
                {"id": job_id, "owner": uuid4(), "lineage": _LINEAGE, "revision": revision},
            )
    finally:
        await engine.dispose()
    return job_id


async def _rows(database_url: str) -> set[tuple[str, int | None]]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT id::text, workspace_document_revision "
                    "FROM exam_answer_key_enrichment_jobs"
                )
            )
    finally:
        await engine.dispose()
    return {(row[0], row[1]) for row in rows.fetchall()}


async def _workspace_indexes(database_url: str) -> dict[str, str]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text(
                    """
                    SELECT indexname, indexdef FROM pg_indexes
                    WHERE tablename = 'exam_answer_key_enrichment_jobs'
                      AND indexname LIKE '%workspace_revision'
                    """
                )
            )
    finally:
        await engine.dispose()
    return {row[0]: row[1] for row in rows.fetchall()}


@pytest.mark.docker
def test_migration_allows_several_jobs_per_saved_version_and_keeps_rows(
    postgres_container: PostgresContainer,
) -> None:
    database_url = _to_async_database_url(postgres_container.get_connection_url())
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    config = _alembic_config(database_url=database_url)
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        command.upgrade(config, _PARENT_REVISION)
        old_job = asyncio.run(_insert_workspace_job(database_url, None))
        asyncio.run(_insert_workspace_job(database_url, 3))
        with pytest.raises(IntegrityError):
            asyncio.run(_insert_workspace_job(database_url, 3))
        before = asyncio.run(_rows(database_url))

        command.upgrade(config, _REVISION_ID)
        command.upgrade(config, _REVISION_ID)

        assert asyncio.run(_rows(database_url)) == before
        assert (str(old_job), None) in before
        indexes = asyncio.run(_workspace_indexes(database_url))
        assert set(indexes) == {"ix_exam_answer_key_enrichment_jobs_workspace_revision"}
        definition = indexes["ix_exam_answer_key_enrichment_jobs_workspace_revision"]
        assert "UNIQUE" not in definition
        assert "created_at" in definition
        asyncio.run(_insert_workspace_job(database_url, 3))
        assert len(asyncio.run(_rows(database_url))) == len(before) + 1
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
