from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
        await conn.execute(text("SELECT COUNT(*) FROM tool_versions"))
        await conn.execute(
            text(
                "SELECT tool_id, version_number, state, source_code, entrypoint, content_hash, "
                "settings_schema, input_schema, usage_instructions, "
                "derived_from_version_id, created_by_user_id, created_at, "
                "submitted_for_review_by_user_id, submitted_for_review_at, "
                "reviewed_by_user_id, reviewed_at, published_by_user_id, published_at, "
                "change_summary, review_note "
                "FROM tool_versions LIMIT 0"
            )
        )

        await conn.execute(text("SELECT COUNT(*) FROM sandbox_snapshots"))
        await conn.execute(
            text(
                "SELECT tool_id, draft_head_id, created_by_user_id, entrypoint, source_code, "
                "settings_schema, input_schema, usage_instructions, payload_bytes, "
                "created_at, expires_at "
                "FROM sandbox_snapshots LIMIT 0"
            )
        )


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


async def _insert_legacy_null_rows(
    *,
    database_url: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    version_sql_null_id = uuid.uuid4()
    version_json_null_id = uuid.uuid4()
    snapshot_sql_null_id = uuid.uuid4()
    snapshot_json_null_id = uuid.uuid4()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider, external_id) "
                    "VALUES (:id, :email, :role, :auth_provider, NULL)"
                ),
                {
                    "id": user_id,
                    "email": "migration-0023@example.com",
                    "role": "superuser",
                    "auth_provider": "local",
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO tools (id, owner_user_id, slug, title, summary) "
                    "VALUES (:id, :owner_user_id, :slug, :title, NULL)"
                ),
                {
                    "id": tool_id,
                    "owner_user_id": user_id,
                    "slug": "migration-0023-tool",
                    "title": "Migration 0023 Tool",
                },
            )
            for version_id, version_number, input_schema_literal in [
                (version_sql_null_id, 1, "NULL"),
                (version_json_null_id, 2, "'null'::jsonb"),
            ]:
                await conn.execute(
                    text(
                        "INSERT INTO tool_versions ("
                        "id, tool_id, version_number, state, source_code, entrypoint, "
                        "content_hash, settings_schema, input_schema, usage_instructions, "
                        "derived_from_version_id, "
                        "created_by_user_id"
                        ") VALUES ("
                        ":id, :tool_id, :version_number, 'draft', :source_code, :entrypoint, "
                        ":content_hash, NULL, "
                        f"{input_schema_literal}, NULL, NULL, :created_by_user_id"
                        ")"
                    ),
                    {
                        "id": version_id,
                        "tool_id": tool_id,
                        "version_number": version_number,
                        "source_code": "print('hi')",
                        "entrypoint": "run_tool",
                        "content_hash": "0" * 64,
                        "created_by_user_id": user_id,
                    },
                )
            for snapshot_id, draft_head_id, input_schema_literal in [
                (snapshot_sql_null_id, version_sql_null_id, "NULL"),
                (snapshot_json_null_id, version_json_null_id, "'null'::jsonb"),
            ]:
                await conn.execute(
                    text(
                        "INSERT INTO sandbox_snapshots ("
                        "id, tool_id, draft_head_id, created_by_user_id, entrypoint, source_code, "
                        "settings_schema, input_schema, usage_instructions, payload_bytes, "
                        "expires_at"
                        ") VALUES ("
                        ":id, :tool_id, :draft_head_id, :created_by_user_id, :entrypoint, "
                        ":source_code, "
                        f"NULL, {input_schema_literal}, NULL, :payload_bytes, :expires_at"
                        ")"
                    ),
                    {
                        "id": snapshot_id,
                        "tool_id": tool_id,
                        "draft_head_id": draft_head_id,
                        "created_by_user_id": user_id,
                        "entrypoint": "run_tool",
                        "source_code": "print('snapshot')",
                        "payload_bytes": 128,
                        "expires_at": expires_at,
                    },
                )
    finally:
        await engine.dispose()

    return (
        version_sql_null_id,
        version_json_null_id,
        snapshot_sql_null_id,
        snapshot_json_null_id,
    )


@pytest.mark.docker
def test_migration_0023_input_schema_not_null_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "0022_email_verification_tokens")
        (
            version_sql_null_id,
            version_json_null_id,
            snapshot_sql_null_id,
            snapshot_json_null_id,
        ) = asyncio.run(_insert_legacy_null_rows(database_url=database_url))

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        engine = create_async_engine(database_url, pool_pre_ping=True)
        try:

            async def _assert_migrated() -> None:
                async with engine.connect() as conn:
                    for version_id in [version_sql_null_id, version_json_null_id]:
                        version_schema = (
                            await conn.execute(
                                text("SELECT input_schema FROM tool_versions WHERE id = :id"),
                                {"id": version_id},
                            )
                        ).scalar_one()
                        assert isinstance(version_schema, list)
                        assert version_schema[0]["kind"] == "file"
                        assert version_schema[0]["min"] == 1

                    for snapshot_id in [snapshot_sql_null_id, snapshot_json_null_id]:
                        snapshot_schema = (
                            await conn.execute(
                                text("SELECT input_schema FROM sandbox_snapshots WHERE id = :id"),
                                {"id": snapshot_id},
                            )
                        ).scalar_one()
                        assert isinstance(snapshot_schema, list)
                        assert snapshot_schema[0]["kind"] == "file"
                        assert snapshot_schema[0]["min"] == 1

                    tool_versions_nullable = (
                        await conn.execute(
                            text(
                                "SELECT is_nullable FROM information_schema.columns "
                                "WHERE table_name = 'tool_versions' "
                                "AND column_name = 'input_schema'"
                            )
                        )
                    ).scalar_one()
                    assert tool_versions_nullable == "NO"

                    sandbox_snapshots_nullable = (
                        await conn.execute(
                            text(
                                "SELECT is_nullable FROM information_schema.columns "
                                "WHERE table_name = 'sandbox_snapshots' "
                                "AND column_name = 'input_schema'"
                            )
                        )
                    ).scalar_one()
                    assert sandbox_snapshots_nullable == "NO"

            asyncio.run(_assert_migrated())
        finally:
            asyncio.run(engine.dispose())

        asyncio.run(_smoke_schema_from_url(database_url=database_url))

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_smoke_schema_from_url(database_url=database_url))
