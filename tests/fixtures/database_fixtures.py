"""Shared Postgres test fixtures for integration repositories and CLI tests.

Each pytest worker process starts at most one Postgres server, and only when a test asks for a
database. The server hosts a migrated template database (``alembic upgrade head`` runs once per
worker). Every module that needs a migrated database receives its own copy of that template, and
every test or module that needs an empty database receives a fresh one. Databases are dropped at
fixture teardown, so no test shares mutable database state with another.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from docker import DockerClient
from docker.errors import DockerException
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from tests.fixtures.orm_models import load_all_models

load_all_models()

_ADMIN_DATABASE = "postgres"
_TEMPLATE_DATABASE = "skriptoteket_migrated_template"


@dataclass(frozen=True)
class PooledDatabase:
    """One database on the worker's shared Postgres server."""

    name: str
    url: str


def _ensure_docker_daemon_available() -> None:
    """Skip DB integration fixtures when the local Docker daemon is unavailable.

    The integration repository tests rely on testcontainers, which shells out through the Docker
    Python SDK. Local dev environments without a running daemon should skip these fixtures instead
    of failing pre-commit/unit-focused checks.
    """
    client: DockerClient | None = None
    try:
        client = DockerClient.from_env()
        client.ping()
    except DockerException:
        pytest.skip("Docker daemon is unavailable; skipping integration DB fixtures.")
    finally:
        if client is not None:
            client.close()


def alembic_config_for(*, database_url: str) -> Config:
    """Return the repository Alembic config pointed at ``database_url``."""
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _run_in_thread[T](make_coroutine: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine to completion in its own thread, so a running loop never conflicts."""
    results: list[T] = []
    failures: list[BaseException] = []

    async def run() -> T:
        return await make_coroutine()

    def target() -> None:
        try:
            results.append(asyncio.run(run()))
        except BaseException as exc:  # noqa: BLE001 - re-raised in the calling thread
            failures.append(exc)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if failures:
        raise failures[0]
    return results[0]


class PostgresServer:
    """The worker's Postgres container plus the admin operations on its databases."""

    def __init__(self, container: PostgresContainer) -> None:
        self._container = container
        base = make_url(container.get_connection_url(driver="asyncpg"))
        self._base = base
        self._admin_url = base.set(database=_ADMIN_DATABASE).render_as_string(hide_password=False)

    def database(self, name: str) -> PooledDatabase:
        url = self._base.set(database=name).render_as_string(hide_password=False)
        return PooledDatabase(name=name, url=url)

    def create_database(self, *, template: str | None = None) -> PooledDatabase:
        """Create an empty database, or a copy of ``template`` (which must have no sessions)."""
        name = f"t_{uuid4().hex}"
        statement = f'CREATE DATABASE "{name}"'
        if template is not None:
            statement += f' TEMPLATE "{template}"'
        self._execute_admin(statement)
        return self.database(name)

    def create_named_database(self, name: str) -> PooledDatabase:
        self._execute_admin(f'CREATE DATABASE "{name}"')
        return self.database(name)

    def drop_database(self, database: PooledDatabase) -> None:
        self._execute_admin(f'DROP DATABASE IF EXISTS "{database.name}" WITH (FORCE)')

    def _execute_admin(self, statement: str) -> None:
        async def run() -> None:
            engine = create_async_engine(self._admin_url, isolation_level="AUTOCOMMIT")
            try:
                async with engine.connect() as connection:
                    await connection.execute(text(statement))
            finally:
                await engine.dispose()

        _run_in_thread(run)


@pytest.fixture(scope="session")
def postgres_server() -> Iterator[PostgresServer]:
    """Start one Postgres server for this worker, the first time a test needs a database."""
    _ensure_docker_daemon_available()
    with PostgresContainer("postgres:16") as container:
        yield PostgresServer(container)


@pytest.fixture(scope="session")
def migrated_template(postgres_server: PostgresServer) -> PooledDatabase:
    """Migrate one database to head for this worker; later databases copy it.

    Alembic runs with a null pool and closes its connections, so the template has no open sessions
    when ``CREATE DATABASE ... TEMPLATE`` copies it.
    """
    template = postgres_server.create_named_database(_TEMPLATE_DATABASE)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", template.url)
        migrate_to_head(alembic_config_for(database_url=template.url), template.url)
    return template


@pytest.fixture(scope="module")
def empty_module_database(postgres_server: PostgresServer) -> Iterator[PooledDatabase]:
    """Yield a fresh, empty database for the test module."""
    database = postgres_server.create_database()
    yield database
    postgres_server.drop_database(database)


@pytest.fixture
def fresh_database(postgres_server: PostgresServer) -> Iterator[PooledDatabase]:
    """Yield a fresh, empty database for one test."""
    database = postgres_server.create_database()
    yield database
    postgres_server.drop_database(database)


@pytest.fixture(scope="module")
def database_url(
    postgres_server: PostgresServer, migrated_template: PooledDatabase
) -> Iterator[str]:
    """Yield the URL of this module's own migrated copy of the template database."""
    database = postgres_server.create_database(template=migrated_template.name)
    yield database.url
    postgres_server.drop_database(database)


@pytest.fixture(scope="module")
def alembic_config(database_url: str) -> Config:
    return alembic_config_for(database_url=database_url)


def _run_alembic_upgrade_in_thread(alembic_config: Config) -> None:
    """Run ``alembic upgrade head`` in a thread and re-raise its exception after join."""
    failures: list[BaseException] = []

    def run_upgrade() -> None:
        try:
            command.upgrade(alembic_config, "head")
        except BaseException as exc:  # noqa: BLE001 - re-raised in the calling thread
            failures.append(exc)

    # Run in a separate thread to avoid asyncio loop conflicts with env.py
    thread = threading.Thread(target=run_upgrade)
    thread.start()
    thread.join()
    if failures:
        raise failures[0]


def migrate_to_head(alembic_config: Config, database_url: str) -> str:
    """Upgrade the database to head and return its URL; a migration error propagates."""

    # Ensure env.py picks up the correct URL
    os.environ["DATABASE_URL"] = database_url

    _run_alembic_upgrade_in_thread(alembic_config)

    return database_url


@pytest.fixture(scope="module")
def migrated_db(database_url: str) -> Iterator[str]:
    """Yield the module's migrated database URL, with ``DATABASE_URL`` pointing at it."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", database_url)
        yield database_url


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
