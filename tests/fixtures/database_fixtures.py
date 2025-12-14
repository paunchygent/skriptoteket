from __future__ import annotations

import os
import threading
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]


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


@pytest.fixture(scope="module")
def postgres_container() -> Iterator[PostgresContainer]:
    """Starts a Postgres container for the test module."""
    with PostgresContainer("postgres:16") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def database_url(postgres_container: PostgresContainer) -> str:
    return _to_async_database_url(postgres_container.get_connection_url())


@pytest.fixture(scope="module")
def alembic_config(database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture(scope="module")
def migrated_db(alembic_config: Config, database_url: str) -> str:
    """Runs alembic upgrade head once for the module."""

    # Ensure env.py picks up the correct URL
    os.environ["DATABASE_URL"] = database_url

    def run_upgrade() -> None:
        command.upgrade(alembic_config, "head")

    # Run in a separate thread to avoid asyncio loop conflicts with env.py
    thread = threading.Thread(target=run_upgrade)
    thread.start()
    thread.join()

    return database_url


@pytest.fixture(scope="module")
async def async_engine(migrated_db: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_db, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="function")
async def db_session(
    session_factory: async_sessionmaker[AsyncSession], async_engine: AsyncEngine
) -> AsyncIterator[AsyncSession]:
    """Yields a database session. Truncates tables after the test."""
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()

    # Cleanup: Truncate all tables to ensure isolation
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        tables = [row[0] for row in result.fetchall()]

        if tables:
            table_list = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(text(f"TRUNCATE TABLE {table_list} CASCADE"))
