from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    run_id = uuid4()
    session_id = uuid4()

    async with engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT id, tool_id, version_id, source_kind, curated_app_id, curated_app_version "
                "FROM tool_runs LIMIT 0"
            )
        )
        await conn.execute(
            text(
                "SELECT id, tool_id, user_id, context, state, state_rev FROM tool_sessions LIMIT 0"
            )
        )

        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0010-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        # Ensure tool_id FKs were removed for curated apps (no tools row needed).
        await conn.execute(
            text(
                "INSERT INTO tool_sessions (id, tool_id, user_id, context, state, state_rev) "
                "VALUES (:id, :tool_id, :user_id, :context, :state, :state_rev)"
            ),
            {
                "id": session_id,
                "tool_id": tool_id,
                "user_id": user_id,
                "context": "default",
                "state": json.dumps({}),
                "state_rev": 0,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO tool_runs ("
                "id, tool_id, version_id, source_kind, curated_app_id, curated_app_version, "
                "context, requested_by_user_id, status, workdir_path, input_filename, "
                "input_size_bytes, "
                "artifacts_manifest"
                ") VALUES ("
                ":id, :tool_id, :version_id, :source_kind, :curated_app_id, :curated_app_version, "
                ":context, :requested_by_user_id, :status, :workdir_path, :input_filename, "
                ":input_size_bytes, "
                ":artifacts_manifest"
                ")"
            ),
            {
                "id": run_id,
                "tool_id": tool_id,
                "version_id": None,
                "source_kind": "curated_app",
                "curated_app_id": "demo.counter",
                "curated_app_version": "test",
                "context": "production",
                "requested_by_user_id": user_id,
                "status": "succeeded",
                "workdir_path": str(run_id),
                "input_filename": "input.bin",
                "input_size_bytes": 0,
                "artifacts_manifest": json.dumps({"artifacts": []}),
            },
        )


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0010_curated_apps_runs_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    monkeypatch.setenv("DATABASE_URL", database_url)

    alembic_cfg = alembic_config_for(database_url=database_url)

    command.upgrade(alembic_cfg, "0009_tool_sessions")
    command.upgrade(alembic_cfg, "0010_curated_apps_runs")
    command.upgrade(alembic_cfg, "0010_curated_apps_runs")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))

    command.downgrade(alembic_cfg, "0009_tool_sessions")
    command.upgrade(alembic_cfg, "0010_curated_apps_runs")

    asyncio.run(_smoke_schema_from_url(database_url=database_url))
