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

    async with engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT email_verified, failed_login_attempts, locked_until, "
                "last_login_at, last_failed_login_at FROM users LIMIT 0"
            )
        )
        await conn.execute(
            text(
                "SELECT user_id, first_name, last_name, display_name, locale, "
                "created_at, updated_at FROM user_profiles LIMIT 0"
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
                "email": f"migration-0013-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        await conn.execute(
            text(
                "INSERT INTO user_profiles (user_id, first_name, last_name, display_name) "
                "VALUES (:user_id, :first_name, :last_name, :display_name)"
            ),
            {
                "user_id": user_id,
                "first_name": "Aina",
                "last_name": "Klockar",
                "display_name": "Aina",
            },
        )

        result = await conn.execute(
            text("SELECT email_verified, failed_login_attempts FROM users WHERE id = :id"),
            {"id": user_id},
        )
        email_verified, failed_login_attempts = result.one()
        assert email_verified is False
        assert failed_login_attempts == 0

        result = await conn.execute(
            text("SELECT locale, created_at, updated_at FROM user_profiles WHERE user_id = :id"),
            {"id": user_id},
        )
        locale, created_at, updated_at = result.one()
        assert locale == "sv-SE"
        assert created_at is not None
        assert updated_at is not None


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0013_user_profiles_and_security_is_idempotent(
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
