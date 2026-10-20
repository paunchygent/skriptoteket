"""Alembic coverage for realm-aware identity projections.

Purpose:
    Prove PR-0258 creates projection/audit tables, backfills legacy HuleEdu
    users before dropping `users.external_id`, and fails ambiguous rows closed.

Relationships:
    - Covers migration `e7b3a9c4d1f2`.
    - Asserts the backfilled projection rows resolve the legacy subject
      to the seeded user through raw SQL at this revision.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for

_REVISION = "e7b3a9c4d1f2"
_PARENT_REVISION = "c1d2e3f4a5b6"


@contextmanager
def _database_url_env(database_url: str) -> Iterator[None]:
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        yield
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


async def _insert_user(database_url: str, values: Mapping[str, object]) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users
                        (id, email, role, auth_provider, external_id, password_hash,
                         is_active, email_verified, created_at, updated_at)
                    VALUES
                        (:id, :email, :role, :auth_provider, :external_id, NULL,
                         true, true, :created_at, :updated_at)
                    """
                ),
                dict(values),
            )
    finally:
        await engine.dispose()


async def _drop_legacy_unique(database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE users DROP CONSTRAINT uq_users_auth_provider_external_id")
            )
    finally:
        await engine.dispose()


async def _assert_backfill(database_url: str, *, user_id: UUID, subject: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            columns = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users'
                    """
                )
            )
            assert "external_id" not in {row[0] for row in columns.fetchall()}

            projection = await conn.execute(
                text(
                    """
                    SELECT user_id, product_identity_realm, realm_subject_id
                    FROM identity_projections
                    WHERE product_identity_realm = 'huleedu_school'
                      AND realm_subject_id = :subject
                    """
                ),
                {"subject": subject},
            )
            assert projection.mappings().one() == {
                "user_id": user_id,
                "product_identity_realm": "huleedu_school",
                "realm_subject_id": subject,
            }

            events = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM identity_projection_events
                    WHERE event_type = 'migration_backfilled'
                      AND realm_subject_id = :subject
                    """
                ),
                {"subject": subject},
            )
            assert int(events.scalar_one()) == 1
    finally:
        await engine.dispose()


async def _assert_projection_resolves_to_user(
    database_url: str,
    *,
    user_id: UUID,
    subject: str,
) -> None:
    """Prove the backfilled subject resolves to the seeded user via raw SQL."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text(
                    """
                    SELECT user_id
                    FROM identity_projections
                    WHERE product_identity_realm = 'huleedu_school'
                      AND realm_subject_id = :subject
                    """
                ),
                {"subject": subject},
            )
            assert [row[0] for row in rows.fetchall()] == [user_id]
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_e7b3a9c4d1f2_backfills_and_removes_external_id(
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    with _database_url_env(database_url):
        alembic_cfg = alembic_config_for(database_url=database_url)
        command.upgrade(alembic_cfg, _PARENT_REVISION)

        user_id = uuid4()
        subject = "legacy-huleedu-subject"
        now = datetime.now(timezone.utc)
        asyncio.run(
            _insert_user(
                database_url,
                {
                    "id": user_id,
                    "email": "migration-teacher@example.test",
                    "role": "contributor",
                    "auth_provider": "huleedu",
                    "external_id": subject,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        )

        command.upgrade(alembic_cfg, _REVISION)
        asyncio.run(_assert_backfill(database_url, user_id=user_id, subject=subject))
        asyncio.run(
            _assert_projection_resolves_to_user(
                database_url,
                user_id=user_id,
                subject=subject,
            )
        )

        command.downgrade(alembic_cfg, _PARENT_REVISION)
        command.upgrade(alembic_cfg, _REVISION)
        asyncio.run(_assert_backfill(database_url, user_id=user_id, subject=subject))


@pytest.mark.docker
@pytest.mark.parametrize(
    ("name", "rows", "drop_unique"),
    [
        pytest.param(
            "blank-huleedu-external-id",
            [
                {
                    "email": "blank-huleedu@example.test",
                    "role": "user",
                    "auth_provider": "huleedu",
                    "external_id": None,
                }
            ],
            False,
            id="blank-huleedu-external-id",
        ),
        pytest.param(
            "unexpected-local-external-id",
            [
                {
                    "email": "unexpected-local@example.test",
                    "role": "user",
                    "auth_provider": "local",
                    "external_id": "legacy-local-subject",
                }
            ],
            False,
            id="unexpected-local-external-id",
        ),
        pytest.param(
            "duplicate-huleedu-external-id",
            [
                {
                    "email": "duplicate-one@example.test",
                    "role": "user",
                    "auth_provider": "huleedu",
                    "external_id": "duplicate-subject",
                },
                {
                    "email": "duplicate-two@example.test",
                    "role": "user",
                    "auth_provider": "huleedu",
                    "external_id": "duplicate-subject",
                },
            ],
            True,
            id="duplicate-huleedu-external-id",
        ),
    ],
)
def test_migration_e7b3a9c4d1f2_fails_ambiguous_legacy_subjects(
    name: str,
    rows: list[dict[str, object]],
    drop_unique: bool,
    fresh_database: PooledDatabase,
) -> None:
    database_url = fresh_database.url
    with _database_url_env(database_url):
        alembic_cfg = alembic_config_for(database_url=database_url)
        command.upgrade(alembic_cfg, _PARENT_REVISION)
        if drop_unique:
            asyncio.run(_drop_legacy_unique(database_url))

        now = datetime.now(timezone.utc)
        for row in rows:
            asyncio.run(
                _insert_user(
                    database_url,
                    {
                        "id": uuid4(),
                        "created_at": now,
                        "updated_at": now,
                        **row,
                    },
                )
            )

        with pytest.raises(RuntimeError, match="Cannot migrate"):
            command.upgrade(alembic_cfg, _REVISION)
