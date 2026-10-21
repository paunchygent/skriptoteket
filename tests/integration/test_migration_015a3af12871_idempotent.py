"""Retiring the retired converter deletes its ledger rows and the retry identity."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import (
    _reset_public_schema,
    assert_revision_is_idempotent,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_T = TypeVar("_T")

_REVISION = "015a3af12871"
_PARENT = "52f2fe74483a"


async def _column_exists(engine: AsyncEngine, *, table: str, column: str) -> bool:
    async with engine.connect() as connection:
        return bool(
            await connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = :table AND column_name = :column)"
                ),
                {"table": table, "column": column},
            )
        )


async def _job_rows(engine: AsyncEngine) -> set[tuple[str, str, str]]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT id::text, source_format, output_format FROM conversion_hub_jobs")
        )
        return {(row[0], row[1], row[2]) for row in result}


async def _saved_transcript_job_ids(engine: AsyncEngine) -> set[UUID]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT conversion_hub_job_id FROM conversion_hub_saved_transcripts")
        )
        return {row[0] for row in result}


async def _assert_retired_schema(
    engine: AsyncEngine, *, kept: set[tuple[str, str, str]], kept_transcript_job: UUID
) -> None:
    rows = await _job_rows(engine)
    assert rows == kept
    assert await _saved_transcript_job_ids(engine) == {kept_transcript_job}
    assert not await _column_exists(
        engine, table="exam_answer_key_enrichment_jobs", column="retry_identity"
    )


async def _assert_prior_schema(engine: AsyncEngine) -> None:
    assert await _column_exists(
        engine, table="exam_answer_key_enrichment_jobs", column="retry_identity"
    )


def test_migration_015a3af12871_is_idempotent(
    empty_module_database: PooledDatabase,
) -> None:
    async def _assert(engine: AsyncEngine) -> None:
        rows = await _job_rows(engine)
        assert all(source != "dxe" and output != "examnet_bundle" for _, source, output in rows)
        assert not await _column_exists(
            engine, table="exam_answer_key_enrichment_jobs", column="retry_identity"
        )

    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION,
        schema_assertion=_assert,
    )


async def _seed_parent_rows(engine: AsyncEngine) -> tuple[set[tuple[str, str, str]], UUID]:
    retired_dxe_bundle = (str(uuid4()), "dxe", "examnet_bundle")
    retired_dxe_pdf = (str(uuid4()), "dxe", "pdf")
    retired_audio_bundle = (str(uuid4()), "audio", "examnet_bundle")
    kept_docx_pdf = (str(uuid4()), "docx", "pdf")
    kept_transcript = (str(uuid4()), "transcript_json", "transcript_bundle")
    owner = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO users (id, email, role, auth_provider) "
                "VALUES (:id, :email, 'user', 'local')"
            ),
            {"id": owner, "email": f"{owner}@example.test"},
        )
        for job_id, source, output in (
            retired_dxe_bundle,
            retired_dxe_pdf,
            retired_audio_bundle,
            kept_docx_pdf,
            kept_transcript,
        ):
            await connection.execute(
                text(
                    "INSERT INTO conversion_hub_jobs "
                    "(id, owner_user_id, input_filename, source_format, output_format, status) "
                    "VALUES (:id, :owner, 'exam.dxe', :source, :output, 'succeeded')"
                ),
                {"id": job_id, "owner": owner, "source": source, "output": output},
            )
        for transcript_job_id, sir_job_id, filename in (
            (retired_dxe_bundle[0], "sir-retired", "old.dxe"),
            (kept_transcript[0], "sir-1", "talk.m4a"),
        ):
            await connection.execute(
                text(
                    "INSERT INTO conversion_hub_saved_transcripts "
                    "(id, owner_user_id, conversion_hub_job_id, sir_convert_job_id, "
                    "artifact_key, source_filename, transcript_schema_version, "
                    "diarization_mode, transcript_json) "
                    "VALUES (:id, :owner, :job, :sir_job, 'audio/transcript.json', "
                    ":filename, 'v1', 'off', '{}'::jsonb)"
                ),
                {
                    "id": uuid4(),
                    "owner": owner,
                    "job": transcript_job_id,
                    "sir_job": sir_job_id,
                    "filename": filename,
                },
            )
        await connection.execute(
            text(
                "INSERT INTO exam_answer_key_enrichment_jobs "
                "(id, owner_user_id, source_kind, status, input_filename, "
                "workspace_lineage_id, workspace_document_revision, retry_identity) "
                "VALUES (:id, :owner, 'workspace', 'queued', 'Prov', :lineage, 1, 'retry-1')"
            ),
            {"id": uuid4(), "owner": owner, "lineage": uuid4()},
        )
    kept = {kept_docx_pdf, kept_transcript}
    return kept, UUID(kept_transcript[0])


async def _with_engine(database_url: str, action: Callable[[AsyncEngine], Awaitable[_T]]) -> _T:
    engine = create_async_engine(database_url)
    try:
        return await action(engine)
    finally:
        await engine.dispose()


def test_migration_015a3af12871_deletes_retired_rows_and_retry_identity(
    empty_module_database: PooledDatabase,
) -> None:
    database_url = empty_module_database.url
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        config = alembic_config_for(database_url=database_url)
        command.upgrade(config, _PARENT)
        kept, kept_transcript_job = asyncio.run(_with_engine(database_url, _seed_parent_rows))

        command.upgrade(config, _REVISION)
        asyncio.run(
            _with_engine(
                database_url,
                lambda engine: _assert_retired_schema(
                    engine, kept=kept, kept_transcript_job=kept_transcript_job
                ),
            )
        )

        command.downgrade(config, _PARENT)
        asyncio.run(_with_engine(database_url, _assert_prior_schema))
        assert asyncio.run(_with_engine(database_url, _job_rows)) == kept

        command.upgrade(config, _REVISION)
        asyncio.run(
            _with_engine(
                database_url,
                lambda engine: _assert_retired_schema(
                    engine, kept=kept, kept_transcript_job=kept_transcript_job
                ),
            )
        )
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
