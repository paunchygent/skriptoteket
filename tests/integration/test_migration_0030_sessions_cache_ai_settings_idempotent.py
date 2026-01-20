from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

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


async def _seed_user_profile_and_session(*, engine: AsyncEngine) -> tuple[UUID, UUID]:
    user_id = uuid4()
    session_id = uuid4()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, role, auth_provider) "
                "VALUES (:id, :email, :role, :auth_provider)"
            ),
            {
                "id": user_id,
                "email": f"{user_id}@example.test",
                "role": "user",
                "auth_provider": "local",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO user_profiles (user_id, allow_remote_fallback, "
                "inline_completion_provider) "
                "VALUES (:user_id, :allow_remote_fallback, :inline_completion_provider)"
            ),
            {
                "user_id": user_id,
                "allow_remote_fallback": True,
                "inline_completion_provider": "external",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO sessions (id, user_id, csrf_token, expires_at) "
                "VALUES (:id, :user_id, :csrf_token, now() + interval '1 day')"
            ),
            {"id": session_id, "user_id": user_id, "csrf_token": "csrf"},
        )

    return user_id, session_id


async def _assert_sessions_ai_cache_columns_exist(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        allow_remote = await conn.execute(
            text(
                "SELECT data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'sessions' AND column_name = 'allow_remote_fallback'"
            )
        )
        assert allow_remote.scalar_one_or_none() == "boolean"

        provider = await conn.execute(
            text(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'sessions' AND column_name = 'inline_completion_provider'"
            )
        )
        assert provider.scalar_one_or_none() == 16


async def _assert_session_was_backfilled(
    *,
    engine: AsyncEngine,
    user_id: UUID,
    expected_allow_remote_fallback: bool | None,
    expected_provider: str | None,
) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT allow_remote_fallback, inline_completion_provider "
                "FROM sessions WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        )
        row = result.one()
        assert row[0] == expected_allow_remote_fallback
        assert row[1] == expected_provider


async def _assert_migration_0030_effects(*, database_url: str, user_id: UUID) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _assert_sessions_ai_cache_columns_exist(engine=engine)
        await _assert_session_was_backfilled(
            engine=engine,
            user_id=user_id,
            expected_allow_remote_fallback=True,
            expected_provider="external",
        )
    finally:
        await engine.dispose()


async def _seed_user_profile_and_session_from_url(*, database_url: str) -> tuple[UUID, UUID]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await _seed_user_profile_and_session(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0030_sessions_cache_ai_settings_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "0029_profile_inline_completion_provider")
        user_id, _ = asyncio.run(_seed_user_profile_and_session_from_url(database_url=database_url))

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_assert_migration_0030_effects(database_url=database_url, user_id=user_id))

        command.downgrade(alembic_cfg, "base")

        command.upgrade(alembic_cfg, "0029_profile_inline_completion_provider")
        user_id_2, _ = asyncio.run(
            _seed_user_profile_and_session_from_url(database_url=database_url)
        )
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_assert_migration_0030_effects(database_url=database_url, user_id=user_id_2))
