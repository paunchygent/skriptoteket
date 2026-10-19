"""Retiring the old exam converter drops its tables, the dxe lane and dead job columns."""

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

_REVISION = "e8a3c5f1b7d2"
_PARENT = "d71e4a6c9b20"
_DROPPED_TABLES = (
    "exam_converter_correction_intents",
    "exam_converter_correction_sessions",
    "exam_answer_key_proposed_overlays",
)
_KEPT_TABLES = (
    "exam_answer_key_enrichment_jobs",
    "conversion_hub_jobs",
    "public_exam_converter_jobs",
)


async def _table_exists(engine: AsyncEngine, name: str) -> bool:
    async with engine.connect() as connection:
        return bool(
            await connection.scalar(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name})
        )


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


async def _index_exists(engine: AsyncEngine, name: str) -> bool:
    async with engine.connect() as connection:
        return bool(
            await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :name)"),
                {"name": name},
            )
        )


async def _source_kind_default(engine: AsyncEngine) -> str | None:
    async with engine.connect() as connection:
        default = await connection.scalar(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'exam_answer_key_enrichment_jobs' "
                "AND column_name = 'source_kind'"
            )
        )
    return None if default is None else str(default)


async def _assert_retired_schema(engine: AsyncEngine) -> None:
    for table in _DROPPED_TABLES:
        assert not await _table_exists(engine, table), table
    for table in _KEPT_TABLES:
        assert await _table_exists(engine, table), table
    assert not await _column_exists(
        engine, table="exam_answer_key_enrichment_jobs", column="conversion_job_id"
    )
    assert not await _column_exists(
        engine, table="conversion_hub_jobs", column="submission_idempotency_key"
    )
    assert not await _index_exists(engine, "uq_conversion_hub_jobs_owner_submission_key")
    assert await _source_kind_default(engine) is None
    async with engine.connect() as connection:
        leftovers = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' "
                "AND tablename = 'exam_answer_key_enrichment_jobs' "
                "AND indexdef LIKE '%conversion_job_id%'"
            )
        )
        assert leftovers == 0
        dxe_rows = await connection.scalar(
            text("SELECT count(*) FROM exam_answer_key_enrichment_jobs WHERE source_kind = 'dxe'")
        )
        assert dxe_rows == 0


async def _assert_prior_schema(engine: AsyncEngine) -> None:
    for table in (*_DROPPED_TABLES, *_KEPT_TABLES):
        assert await _table_exists(engine, table), table
    assert await _column_exists(
        engine, table="exam_answer_key_enrichment_jobs", column="conversion_job_id"
    )
    assert await _column_exists(
        engine, table="conversion_hub_jobs", column="submission_idempotency_key"
    )
    assert await _index_exists(engine, "uq_conversion_hub_jobs_owner_submission_key")
    default = await _source_kind_default(engine)
    assert default is not None
    assert "dxe" in default


def test_migration_e8a3c5f1b7d2_is_idempotent_and_drops_old_converter_schema(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION,
        schema_assertion=_assert_retired_schema,
    )


async def _seed_parent_rows(engine: AsyncEngine) -> tuple[UUID, UUID]:
    dxe_id, workspace_id = uuid4(), uuid4()
    owner = uuid4()
    async with engine.begin() as connection:
        insert = text(
            "INSERT INTO exam_answer_key_enrichment_jobs "
            "(id, owner_user_id, source_kind, status, input_filename, source_dxe, "
            "workspace_lineage_id, workspace_document_revision) "
            "VALUES (:id, :owner, :kind, 'queued', 'prov', :dxe, :lineage, :revision)"
        )
        await connection.execute(
            insert,
            {
                "id": dxe_id,
                "owner": owner,
                "kind": "dxe",
                "dxe": b"source",
                "lineage": None,
                "revision": None,
            },
        )
        await connection.execute(
            insert,
            {
                "id": workspace_id,
                "owner": owner,
                "kind": "workspace",
                "dxe": None,
                "lineage": uuid4(),
                "revision": 1,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO exam_answer_key_proposed_overlays "
                "(id, enrichment_job_id, owner_user_id, source_file_sha256, source_ir_sha256, "
                "provider_profile_id, model, overlay_json) "
                "VALUES (:id, :job, :owner, 'a', 'b', 'p', 'm', '{}'::jsonb)"
            ),
            {"id": uuid4(), "job": dxe_id, "owner": owner},
        )
    return dxe_id, workspace_id


async def _surviving_job_ids(engine: AsyncEngine) -> set[UUID]:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT id FROM exam_answer_key_enrichment_jobs"))
        return {row[0] for row in result}


async def _with_engine(database_url: str, action: Callable[[AsyncEngine], Awaitable[_T]]) -> _T:
    engine = create_async_engine(database_url)
    try:
        return await action(engine)
    finally:
        await engine.dispose()


def test_migration_e8a3c5f1b7d2_deletes_dxe_rows_keeps_workspace_rows_and_round_trips(
    empty_module_database: PooledDatabase,
) -> None:
    database_url = empty_module_database.url
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        config = alembic_config_for(database_url=database_url)
        command.upgrade(config, _PARENT)
        dxe_id, workspace_id = asyncio.run(_with_engine(database_url, _seed_parent_rows))
        assert dxe_id != workspace_id

        command.upgrade(config, _REVISION)
        asyncio.run(_with_engine(database_url, _assert_retired_schema))
        assert asyncio.run(_with_engine(database_url, _surviving_job_ids)) == {workspace_id}

        command.downgrade(config, _PARENT)
        asyncio.run(_with_engine(database_url, _assert_prior_schema))
        assert asyncio.run(_with_engine(database_url, _surviving_job_ids)) == {workspace_id}

        command.upgrade(config, _REVISION)
        asyncio.run(_with_engine(database_url, _assert_retired_schema))
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
