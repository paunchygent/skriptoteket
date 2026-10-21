"""Dropping the public guest DigiExam converter job table (TASK-SKRIPT-41-02-03)."""

import asyncio
import os

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.migration_idempotency_support import (
    _reset_public_schema,
    assert_revision_is_idempotent,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_REVISION = "52f2fe74483a"
_PARENT = "74adf10e2441"
_TABLE = "public_exam_converter_jobs"
_INDEXES = (
    "ix_public_exam_converter_jobs_claim",
    "ix_public_exam_converter_jobs_expires_at",
    "ix_public_exam_converter_jobs_status",
)
_COLUMNS = {
    "id",
    "status",
    "requested_targets",
    "source_filename",
    "source_content_type",
    "source_dxe",
    "graded_result_filename",
    "graded_result_content_type",
    "graded_result_pdf",
    "correlation_id",
    "error_message",
    "result",
    "locked_by",
    "locked_until",
    "submitted_at",
    "updated_at",
    "expires_at",
}


async def _table_exists(engine: AsyncEngine, name: str) -> bool:
    async with engine.connect() as connection:
        return bool(
            await connection.scalar(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name})
        )


async def _assert_dropped_schema(engine: AsyncEngine) -> None:
    assert not await _table_exists(engine, _TABLE)
    async with engine.connect() as connection:
        leftovers = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename = :table"
            ),
            {"table": _TABLE},
        )
        assert leftovers == 0


async def _assert_present_schema(engine: AsyncEngine) -> None:
    assert await _table_exists(engine, _TABLE)
    async with engine.connect() as connection:
        columns = await connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :table"
            ),
            {"table": _TABLE},
        )
        assert {row[0] for row in columns} == _COLUMNS
        for index in _INDEXES:
            exists = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :name)"),
                {"name": index},
            )
            assert exists, index


def test_migration_52f2fe74483a_is_idempotent_and_drops_public_converter_jobs(
    empty_module_database: PooledDatabase,
) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id=_REVISION,
        schema_assertion=_assert_dropped_schema,
    )


def test_migration_52f2fe74483a_round_trips_public_converter_jobs(
    empty_module_database: PooledDatabase,
) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    database_url = empty_module_database.url
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        config = alembic_config_for(database_url=database_url)
        command.upgrade(config, _PARENT)
        engine = create_async_engine(database_url)
        try:
            asyncio.run(_assert_present_schema(engine))
        finally:
            asyncio.run(engine.dispose())

        command.upgrade(config, _REVISION)
        engine = create_async_engine(database_url)
        try:
            asyncio.run(_assert_dropped_schema(engine))
        finally:
            asyncio.run(engine.dispose())

        command.downgrade(config, _PARENT)
        engine = create_async_engine(database_url)
        try:
            asyncio.run(_assert_present_schema(engine))
        finally:
            asyncio.run(engine.dispose())

        command.upgrade(config, _REVISION)
        engine = create_async_engine(database_url)
        try:
            asyncio.run(_assert_dropped_schema(engine))
        finally:
            asyncio.run(engine.dispose())
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
