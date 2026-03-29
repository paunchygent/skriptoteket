"""Integration coverage for the domain allowlist migration.

Purpose:
    Verify the `5a7c1d9e3b2f` Alembic revision remains idempotent and leaves the
    allowlist tables with the expected schema after repeated upgrades.

Relationships:
    - Exercises `migrations/versions/5a7c1d9e3b2f_add_domain_allowlist_tables.py`.
    - Counts as the dedicated migration coverage for the latest allowlist head.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer

from tests.fixtures.database_fixtures import _to_async_database_url


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _assert_domain_allowlist_schema(*, engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        allowed_columns = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'allowed_domains'
                ORDER BY ordinal_position
                """
            )
        )
        blocked_columns = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'blocked_domains'
                ORDER BY ordinal_position
                """
            )
        )
        allowed_indexes = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'allowed_domains'
                """
            )
        )
        blocked_indexes = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'blocked_domains'
                """
            )
        )

    assert [row[0] for row in allowed_columns.fetchall()] == [
        "domain",
        "org_type",
        "org_name",
        "source",
        "source_ref",
        "is_active",
        "notes",
        "created_at",
        "updated_at",
    ]
    assert [row[0] for row in blocked_columns.fetchall()] == [
        "domain",
        "reason",
        "source",
        "source_ref",
        "is_active",
        "notes",
        "created_at",
        "updated_at",
    ]
    assert {
        "allowed_domains_pkey",
        "ix_allowed_domains_is_active",
        "ix_allowed_domains_org_type",
    } <= {row[0] for row in allowed_indexes.fetchall()}
    assert {"blocked_domains_pkey", "ix_blocked_domains_is_active"} <= {
        row[0] for row in blocked_indexes.fetchall()
    }


async def _assert_domain_allowlist_schema_from_url(*, database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await _assert_domain_allowlist_schema(engine=engine)
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_5a7c1d9e3b2f_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        monkeypatch.setenv("DATABASE_URL", database_url)

        alembic_cfg = _alembic_config(database_url=database_url)

        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_assert_domain_allowlist_schema_from_url(database_url=database_url))

        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        asyncio.run(_assert_domain_allowlist_schema_from_url(database_url=database_url))
