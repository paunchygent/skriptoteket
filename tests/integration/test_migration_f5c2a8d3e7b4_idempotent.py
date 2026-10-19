"""Integration coverage for the workspace suggestion job migration.

Purpose:
    Verify the `f5c2a8d3e7b4` Alembic revision (TASK-SKRIPT-39-04-07, P10)
    deletes only the workspace's rows from
    `exam_answer_key_proposed_overlays` while DigiExam rows stay, and adds
    the sent-content and suggestion columns to the enrichment job table.

Relationships:
    - Exercises
      `migrations/versions/f5c2a8d3e7b4_workspace_suggestion_job_content.py`.
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import _reset_public_schema

_REVISION_ID = "f5c2a8d3e7b4"
_PARENT_REVISION = "c4f8a2d6b9e1"


async def _seed_overlay_rows(database_url: str) -> tuple[str, str]:
    """Insert one workspace overlay row and one DigiExam overlay row."""
    workspace_job_id = uuid4()
    dxe_job_id = uuid4()
    owner_id = uuid4()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            for job_id in (workspace_job_id, dxe_job_id):
                await conn.execute(
                    text(
                        """
                        INSERT INTO exam_answer_key_enrichment_jobs
                            (id, owner_user_id, status, input_filename)
                        VALUES (:id, :owner, 'succeeded', 'prov')
                        """
                    ),
                    {"id": job_id, "owner": owner_id},
                )
            await conn.execute(
                text(
                    """
                    INSERT INTO exam_answer_key_proposed_overlays
                        (id, enrichment_job_id, conversion_job_id, owner_user_id,
                         workspace_lineage_id, workspace_document_revision,
                         source_file_sha256, source_ir_sha256,
                         provider_profile_id, model, overlay_json)
                    VALUES (:id, :job, NULL, :owner, :lineage, 3,
                            'a', 'b', 'p', 'm', '{}'::jsonb)
                    """
                ),
                {
                    "id": uuid4(),
                    "job": workspace_job_id,
                    "owner": owner_id,
                    "lineage": uuid4(),
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO exam_answer_key_proposed_overlays
                        (id, enrichment_job_id, conversion_job_id, owner_user_id,
                         workspace_lineage_id, workspace_document_revision,
                         source_file_sha256, source_ir_sha256,
                         provider_profile_id, model, overlay_json)
                    VALUES (:id, :job, :conversion, :owner, NULL, NULL,
                            'a', 'b', 'p', 'm', '{}'::jsonb)
                    """
                ),
                {
                    "id": uuid4(),
                    "job": dxe_job_id,
                    "conversion": uuid4(),
                    "owner": owner_id,
                },
            )
    finally:
        await engine.dispose()
    return str(workspace_job_id), str(dxe_job_id)


async def _overlay_job_ids(database_url: str) -> set[str]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text("SELECT enrichment_job_id::text FROM exam_answer_key_proposed_overlays")
            )
    finally:
        await engine.dispose()
    return {row[0] for row in rows.fetchall()}


async def _assert_suggestion_columns(database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            columns = await conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'exam_answer_key_enrichment_jobs'
                    """
                )
            )
            column_names = {row[0] for row in columns.fetchall()}
    finally:
        await engine.dispose()
    assert {"workspace_request_json", "workspace_suggestions_json"} <= column_names


@pytest.mark.docker
def test_migration_deletes_only_workspace_overlay_rows(
    empty_module_database: PooledDatabase,
) -> None:
    database_url = empty_module_database.url
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    config = alembic_config_for(database_url=database_url)
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        command.upgrade(config, _PARENT_REVISION)
        workspace_job_id, dxe_job_id = asyncio.run(_seed_overlay_rows(database_url))
        assert asyncio.run(_overlay_job_ids(database_url)) == {workspace_job_id, dxe_job_id}

        command.upgrade(config, _REVISION_ID)
        command.upgrade(config, _REVISION_ID)

        remaining = asyncio.run(_overlay_job_ids(database_url))
        assert remaining == {dxe_job_id}
        asyncio.run(_assert_suggestion_columns(database_url))

        command.downgrade(config, _PARENT_REVISION)
        command.upgrade(config, _REVISION_ID)
        assert asyncio.run(_overlay_job_ids(database_url)) == {dxe_job_id}
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
