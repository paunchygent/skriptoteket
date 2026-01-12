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


async def _seed_pre_0011_run(*, engine: AsyncEngine) -> tuple[str, int]:
    user_id = uuid4()
    tool_id = uuid4()
    run_id = uuid4()
    input_size_bytes = 42

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0011-seed-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        # Insert a ToolRun before input_manifest exists (migration 0011 should backfill it).
        await conn.execute(
            text(
                "INSERT INTO tool_runs ("
                "id, tool_id, version_id, source_kind, curated_app_id, "
                "curated_app_version, context, requested_by_user_id, status, "
                "workdir_path, input_filename, input_size_bytes, artifacts_manifest"
                ") VALUES ("
                ":id, :tool_id, :version_id, :source_kind, :curated_app_id, "
                ":curated_app_version, :context, :requested_by_user_id, :status, "
                ":workdir_path, :input_filename, :input_size_bytes, :artifacts_manifest"
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
                "input_filename": "input.bin",
                "input_size_bytes": input_size_bytes,
                "artifacts_manifest": json.dumps({"artifacts": []}),
            },
        )

    return str(run_id), input_size_bytes


async def _seed_pre_0011_run_from_url(*, database_url: str) -> tuple[str, int]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await _seed_pre_0011_run(engine=engine)
    finally:
        await engine.dispose()


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    run_id = uuid4()

    async with engine.connect() as conn:
        await conn.execute(text("SELECT input_manifest FROM tool_runs LIMIT 0"))

        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0011-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        # input_manifest must have a server default and be non-null.
        await conn.execute(
            text(
                "INSERT INTO tool_runs ("
                "id, tool_id, version_id, source_kind, curated_app_id, "
                "curated_app_version, context, requested_by_user_id, status, "
                "workdir_path, input_filename, input_size_bytes, artifacts_manifest"
                ") VALUES ("
                ":id, :tool_id, :version_id, :source_kind, :curated_app_id, "
                ":curated_app_version, :context, :requested_by_user_id, :status, "
                ":workdir_path, :input_filename, :input_size_bytes, :artifacts_manifest"
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

        result = await conn.execute(
            text("SELECT input_manifest FROM tool_runs WHERE id = :id"),
            {"id": run_id},
        )
        manifest = result.scalar_one()
        if isinstance(manifest, str):
            manifest = json.loads(manifest)
        assert manifest == {"files": []}


async def _cleanup_seeded_run(*, engine: AsyncEngine, run_id: str) -> None:
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT requested_by_user_id FROM tool_runs WHERE id = :id"),
            {"id": run_id},
        )
        user_id = result.scalar_one_or_none()

        await conn.execute(
            text("DELETE FROM tool_runs WHERE id = :id"),
            {"id": run_id},
        )
        if user_id is not None:
            await conn.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": user_id},
            )


async def _cleanup_seeded_run_from_url(*, database_url: str, run_id: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _cleanup_seeded_run(engine=engine, run_id=run_id)
    finally:
        await engine.dispose()


async def _smoke_schema_from_url(
    *,
    database_url: str,
    seeded_run_id: str | None = None,
    seeded_run_input_bytes: int | None = None,
) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)

        if seeded_run_id is None:
            return
        if seeded_run_input_bytes is None:
            raise ValueError("seeded_run_input_bytes is required when seeded_run_id is set")

        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT input_manifest FROM tool_runs WHERE id = :id"),
                {"id": seeded_run_id},
            )
            manifest = result.scalar_one()
            if isinstance(manifest, str):
                manifest = json.loads(manifest)
            assert manifest == {
                "files": [{"name": "input.bin", "bytes": seeded_run_input_bytes}],
            }
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0011_tool_runs_input_manifest_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "0010_curated_apps_runs")
        seeded_run_id, seeded_run_bytes = asyncio.run(
            _seed_pre_0011_run_from_url(database_url=database_url)
        )

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(
            _smoke_schema_from_url(
                database_url=database_url,
                seeded_run_id=seeded_run_id,
                seeded_run_input_bytes=seeded_run_bytes,
            )
        )
        asyncio.run(_cleanup_seeded_run_from_url(database_url=database_url, run_id=seeded_run_id))

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))
