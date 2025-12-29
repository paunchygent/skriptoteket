from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
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


def _column_map(rows: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    return {row[0]: (row[1], row[2]) for row in rows}


async def _smoke_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'login_events'"
            )
        )
        columns = _column_map([cast(tuple[str, str, str], tuple(row)) for row in result.fetchall()])
        assert columns["id"] == ("uuid", "NO")
        assert columns["user_id"] == ("uuid", "YES")
        assert columns["status"] == ("character varying", "NO")
        assert columns["failure_code"] == ("character varying", "YES")
        assert columns["ip_address"] == ("character varying", "YES")
        assert columns["user_agent"] == ("text", "YES")
        assert columns["auth_provider"] == ("character varying", "NO")
        assert columns["correlation_id"] == ("uuid", "YES")
        assert columns["geo_country_code"] == ("character varying", "YES")
        assert columns["geo_region"] == ("character varying", "YES")
        assert columns["geo_city"] == ("character varying", "YES")
        assert columns["geo_latitude"] == ("double precision", "YES")
        assert columns["geo_longitude"] == ("double precision", "YES")
        assert columns["created_at"] == ("timestamp with time zone", "NO")

        user_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO users "
                "(id, email, role, auth_provider, external_id, password_hash, is_active) "
                "VALUES "
                "(:id, :email, :role, :auth_provider, :external_id, :password_hash, :is_active)"
            ),
            {
                "id": user_id,
                "email": f"migration-0021-{user_id.hex[:8]}@example.com",
                "role": "user",
                "auth_provider": "local",
                "external_id": None,
                "password_hash": None,
                "is_active": True,
            },
        )

        event_id = uuid4()
        now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        await conn.execute(
            text(
                "INSERT INTO login_events "
                "(id, user_id, status, failure_code, ip_address, user_agent, auth_provider, "
                "correlation_id, geo_country_code, geo_region, geo_city, geo_latitude, "
                "geo_longitude, created_at) "
                "VALUES "
                "(:id, :user_id, :status, :failure_code, :ip_address, :user_agent, "
                ":auth_provider, :correlation_id, :geo_country_code, :geo_region, :geo_city, "
                ":geo_latitude, :geo_longitude, :created_at)"
            ),
            {
                "id": event_id,
                "user_id": user_id,
                "status": "success",
                "failure_code": None,
                "ip_address": "127.0.0.1",
                "user_agent": "pytest",
                "auth_provider": "local",
                "correlation_id": uuid4(),
                "geo_country_code": None,
                "geo_region": None,
                "geo_city": None,
                "geo_latitude": None,
                "geo_longitude": None,
                "created_at": now,
            },
        )

        result = await conn.execute(
            text("SELECT created_at, status FROM login_events WHERE id = :id"),
            {"id": event_id},
        )
        created_at, status = result.one()
        assert created_at == now
        assert status == "success"


async def _smoke_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _smoke_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_0021_login_events_is_idempotent(
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
