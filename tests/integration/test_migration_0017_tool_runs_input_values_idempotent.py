from __future__ import annotations

import asyncio
import json
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
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_runs' AND column_name = 'input_values'"
            )
        )
        row = result.one_or_none()
        assert row is not None, "input_values column should exist"
        data_type, is_nullable = row
        assert data_type == "jsonb", f"Expected jsonb, got {data_type}"
        assert is_nullable == "NO", f"Expected NOT NULL, got is_nullable={is_nullable}"

        result = await conn.execute(
            text(
                "SELECT is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tool_runs' AND column_name = 'input_filename'"
            )
        )
        row = result.one_or_none()
        assert row is not None, "input_filename column should exist"
        (is_nullable,) = row
        assert is_nullable == "YES", f"Expected nullable, got is_nullable={is_nullable}"

        user_id = uuid4()
        run_id = uuid4()
        tool_id = uuid4()

        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0017-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        await conn.execute(
            text(
                "INSERT INTO tool_runs ("
                "id, tool_id, version_id, source_kind, curated_app_id, curated_app_version, "
                "context, requested_by_user_id, status, workdir_path, "
                "input_filename, input_size_bytes, artifacts_manifest"
                ") VALUES ("
                ":id, :tool_id, :version_id, :source_kind, :curated_app_id, :curated_app_version, "
                ":context, :requested_by_user_id, :status, :workdir_path, "
                ":input_filename, :input_size_bytes, :artifacts_manifest"
                ")"
            ),
            {
                "id": run_id,
                "tool_id": tool_id,
                "version_id": None,
                "source_kind": "curated_app",
                "curated_app_id": "demo.counter",
                "curated_app_version": "seed",
                "context": "production",
                "requested_by_user_id": user_id,
                "status": "succeeded",
                "workdir_path": str(run_id),
                "input_filename": None,
                "input_size_bytes": 0,
                "artifacts_manifest": json.dumps({"artifacts": []}),
            },
        )

        result = await conn.execute(
            text("SELECT input_filename, input_values FROM tool_runs WHERE id = :id"),
            {"id": run_id},
        )
        input_filename, input_values = result.one()
        assert input_filename is None

        if isinstance(input_values, str):
            input_values = json.loads(input_values)
        assert input_values == {}


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0017_tool_runs_input_values_is_idempotent(
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
