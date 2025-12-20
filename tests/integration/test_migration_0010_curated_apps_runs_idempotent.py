from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

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
                "SELECT id, tool_id, user_id, context, state, state_rev "
                "FROM tool_sessions LIMIT 0"
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
                "state": {},
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
                "input_filename": "action.json",
                "input_size_bytes": 0,
                "artifacts_manifest": {"artifacts": []},
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
