from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT COUNT(*) FROM tool_runs"))
        await conn.execute(
            text(
                "SELECT id, tool_id, version_id, context, requested_by_user_id, status, "
                "started_at, finished_at, workdir_path, input_filename, input_size_bytes, "
                "html_output, stdout, stderr, artifacts_manifest, error_summary, ui_payload "
                "FROM tool_runs LIMIT 0"
            )
        )


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0008_tool_runs_ui_payload_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0007_tool_maintainer_audit_log")
    command.upgrade(alembic_cfg, "0008_tool_runs_ui_payload")
    command.upgrade(alembic_cfg, "0008_tool_runs_ui_payload")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0007_tool_maintainer_audit_log")
    command.upgrade(alembic_cfg, "0008_tool_runs_ui_payload")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
