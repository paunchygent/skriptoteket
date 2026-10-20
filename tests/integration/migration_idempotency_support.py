"""Shared helpers for revision-focused Alembic idempotency tests.

This module provides the reset-and-run harness for migration integration tests.
It keeps the coverage tests focused on revision behavior while centralizing the
Alembic config setup, parent-revision discovery, schema reset, and version-table
assertions.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for

SchemaAssertion = Callable[[AsyncEngine], Awaitable[None]]


def _parent_revisions(revision_id: str) -> tuple[str, ...]:
    """Return the parent revision ids of ``revision_id`` (empty tuple for base)."""
    script = ScriptDirectory.from_config(Config(str(Path("alembic.ini"))))
    revision = script.get_revision(revision_id)
    if revision is None:
        raise ValueError(f"Unknown Alembic revision: {revision_id}")
    down_revision = revision.down_revision
    if down_revision is None:
        return ()
    if isinstance(down_revision, str):
        return (down_revision,)
    return tuple(down_revision)


def _downgrade_targets(parent_revisions: tuple[str, ...]) -> tuple[str, ...]:
    """Return the Alembic targets that restore exactly ``parent_revisions``.

    A merge revision downgrades to each parent in turn, because the relative
    ``<rev>-1`` target raises "Ambiguous walk".
    """
    if parent_revisions:
        return parent_revisions
    return ("base",)


async def _reset_public_schema(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.exec_driver_sql("CREATE SCHEMA public")
            await conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO PUBLIC")
    finally:
        await engine.dispose()


async def _assert_version_rows(
    *,
    database_url: str,
    expected: tuple[str, ...],
) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = sorted(row[0] for row in result.fetchall())
        assert rows == sorted(expected)
    finally:
        await engine.dispose()


async def _assert_revision_state(
    *,
    database_url: str,
    revision_id: str,
    schema_assertion: SchemaAssertion,
) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            assert result.scalar_one() == revision_id
        await schema_assertion(engine)
    finally:
        await engine.dispose()


def assert_revision_is_idempotent(
    *,
    empty_module_database: PooledDatabase,
    revision_id: str,
    schema_assertion: SchemaAssertion,
) -> None:
    """Verify a revision upgrade, no-op rerun, downgrade, and re-upgrade cycle."""
    database_url = empty_module_database.url
    parent_revisions = _parent_revisions(revision_id)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url

    try:
        asyncio.run(_reset_public_schema(database_url=database_url))

        alembic_cfg = alembic_config_for(database_url=database_url)
        for parent_revision in parent_revisions:
            command.upgrade(alembic_cfg, parent_revision)

        command.upgrade(alembic_cfg, revision_id)
        command.upgrade(alembic_cfg, revision_id)
        asyncio.run(
            _assert_revision_state(
                database_url=database_url,
                revision_id=revision_id,
                schema_assertion=schema_assertion,
            )
        )

        for downgrade_target in _downgrade_targets(parent_revisions):
            command.downgrade(alembic_cfg, downgrade_target)
        asyncio.run(
            _assert_version_rows(
                database_url=database_url,
                expected=parent_revisions,
            )
        )
        command.upgrade(alembic_cfg, revision_id)
        asyncio.run(
            _assert_revision_state(
                database_url=database_url,
                revision_id=revision_id,
                schema_assertion=schema_assertion,
            )
        )
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
