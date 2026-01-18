from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer


def _to_async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+"):
        prefix, rest = url.split("://", 1)
        base = prefix.split("+", 1)[0]
        return f"{base}+asyncpg://{rest}"
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unsupported database url scheme: {url}")


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _column_map(rows: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {row[0]: (row[1], row[2]) for row in rows}


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_run_jobs'"
            )
        )
        job_columns = _column_map(
            [cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()]
        )
        assert job_columns["id"] == ("uuid", "NO")
        assert job_columns["run_id"] == ("uuid", "NO")
        assert job_columns["status"] == ("character varying", "NO")
        assert job_columns["queue"] == ("character varying", "NO")
        assert job_columns["priority"] == ("integer", "NO")
        assert job_columns["attempts"] == ("integer", "NO")
        assert job_columns["max_attempts"] == ("integer", "NO")
        assert job_columns["available_at"] == ("timestamp with time zone", "NO")
        assert job_columns["locked_by"] == ("character varying", "YES")
        assert job_columns["locked_until"] == ("timestamp with time zone", "YES")
        assert job_columns["last_error"] == ("text", "YES")
        assert job_columns["created_at"] == ("timestamp with time zone", "NO")
        assert job_columns["updated_at"] == ("timestamp with time zone", "NO")
        assert job_columns["started_at"] == ("timestamp with time zone", "YES")
        assert job_columns["finished_at"] == ("timestamp with time zone", "YES")

        result = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'tool_run_jobs' "
                "ORDER BY indexname"
            )
        )
        job_indexes = [row[0] for row in result.fetchall()]
        assert "ix_tool_run_jobs_claim_order" in job_indexes
        assert "ix_tool_run_jobs_run_id" in job_indexes
        assert "ix_tool_run_jobs_stale_lease" in job_indexes
        assert "ix_tool_run_jobs_status" in job_indexes

        result = await conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'tool_run_jobs'::regclass AND contype = 'u'"
            )
        )
        constraints = [row[0] for row in result.fetchall()]
        assert "uq_tool_run_jobs_run_id" in constraints

        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_runs'"
            )
        )
        run_columns = _column_map(
            [cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()]
        )
        assert run_columns["requested_at"] == ("timestamp with time zone", "NO")
        assert run_columns["started_at"] == ("timestamp with time zone", "YES")

        result = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'tool_runs' ORDER BY indexname"
            )
        )
        run_indexes = [row[0] for row in result.fetchall()]
        assert "ix_tool_runs_requested_at" in run_indexes

        await conn.execute(text("SELECT COUNT(*) FROM tool_run_jobs"))


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0027_tool_run_jobs_execution_queue_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))
