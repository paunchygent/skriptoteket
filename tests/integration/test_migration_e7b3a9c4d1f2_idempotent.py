"""Alembic coverage for realm-aware identity projections.

Purpose:
    Prove PR-0258 creates projection/audit tables, backfills legacy HuleEdu
    users before dropping `users.external_id`, and fails ambiguous rows closed.

Relationships:
    - Covers migration `e7b3a9c4d1f2`.
    - Exercises the upgraded projection resolver against backfilled data.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppProjectionResolver
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.profile_repository import PostgreSQLProfileRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from tests.fixtures.database_fixtures import _to_async_database_url

_REVISION = "e7b3a9c4d1f2"
_PARENT_REVISION = "c1d2e3f4a5b6"


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


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


def _context_payload(*, subject: str) -> dict[str, object]:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    return {
        "context_version": 1,
        "iss": "api_gateway_service",
        "aud": "skriptoteket",
        "sub": subject,
        "session_id": "migration-session",
        "roles": ["teacher"],
        "grants": ["tools:run"],
        "policy_version": "2026-04-12",
        "iat": now_ts,
        "exp": now_ts + 60,
        "jti": "migration-context",
        "active_app": "skriptoteket",
        "active_product_identity_realm": "huleedu_school",
        "realm_subject_id": subject,
        "email": "migration-teacher@example.test",
        "email_verified": True,
    }


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


async def _assert_resolver_uses_backfilled_projection(
    database_url: str,
    *,
    user_id: UUID,
    subject: str,
) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            resolver = HuleEduAppProjectionResolver(
                uow=SQLAlchemyUnitOfWork(session),
                users=PostgreSQLUserRepository(session),
                profiles=PostgreSQLProfileRepository(session),
                projections=PostgreSQLIdentityProjectionRepository(session),
                projection_events=PostgreSQLIdentityProjectionEventRepository(session),
                clock=UTCClock(),
                id_generator=UUID4Generator(),
            )
            projection = await resolver.resolve(
                context=InternalIdentityContextV1.model_validate(_context_payload(subject=subject))
            )

        assert projection.user.id == user_id
        assert projection.profile.user_id == user_id
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_migration_e7b3a9c4d1f2_backfills_and_removes_external_id() -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        with _database_url_env(database_url):
            alembic_cfg = _alembic_config(database_url=database_url)
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
                _assert_resolver_uses_backfilled_projection(
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
) -> None:
    with PostgresContainer("postgres:16") as postgres:
        database_url = _to_async_database_url(postgres.get_connection_url())
        with _database_url_env(database_url):
            alembic_cfg = _alembic_config(database_url=database_url)
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
