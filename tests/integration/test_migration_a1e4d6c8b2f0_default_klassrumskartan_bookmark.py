"""Integration coverage for the default Klassrumskartan bookmark backfill.

Purpose:
    Verify that the backfill migration bookmarks Klassrumskartan for existing
    users, preserves already-bookmarked rows, and survives reruns cleanly.

Relationships:
    - Upgrades from the password-reset migration head that currently precedes
      this worktree's bookmark backfill revision.
    - Exercises only `user_favorite_apps` data behavior; schema assertions live
      in the shared migration coverage suite.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.database_fixtures import _to_async_database_url

_TARGET_REVISION = "a1e4d6c8b2f0"
_PARENT_REVISION = "8f3d2c1b4a6e"
_DEFAULT_APP_ID = "classroom.group-seating-studio"


def _alembic_config(*, database_url: str) -> Config:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _seed_existing_users(*, database_url: str) -> tuple[str, str]:
    first_user_id = str(uuid4())
    second_user_id = str(uuid4())
    engine = create_async_engine(database_url, pool_pre_ping=True)

    try:
        async with engine.begin() as conn:
            for user_id in (first_user_id, second_user_id):
                await conn.execute(
                    text(
                        """
                        INSERT INTO users (
                            id,
                            email,
                            role,
                            auth_provider,
                            external_id,
                            password_hash,
                            is_active,
                            email_verified,
                            failed_login_attempts
                        )
                        VALUES (
                            :id,
                            :email,
                            'user',
                            'local',
                            NULL,
                            'hash',
                            true,
                            true,
                            0
                        )
                        """
                    ),
                    {
                        "id": user_id,
                        "email": f"{user_id[:8]}@example.test",
                    },
                )

            await conn.execute(
                text(
                    """
                    INSERT INTO user_favorite_apps (user_id, app_id)
                    VALUES (:user_id, :app_id)
                    """
                ),
                {"user_id": second_user_id, "app_id": _DEFAULT_APP_ID},
            )
    finally:
        await engine.dispose()

    return first_user_id, second_user_id


async def _count_default_rows(*, database_url: str) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM user_favorite_apps WHERE app_id = :app_id"),
                {"app_id": _DEFAULT_APP_ID},
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _count_user_default_rows(*, database_url: str, user_id: str) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM user_favorite_apps
                    WHERE user_id = :user_id AND app_id = :app_id
                    """
                ),
                {"user_id": user_id, "app_id": _DEFAULT_APP_ID},
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.docker
def test_default_klassrumskartan_bookmark_migration_backfills_existing_users(
    postgres_container,
) -> None:
    database_url = _to_async_database_url(postgres_container.get_connection_url())
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url

    alembic_cfg = _alembic_config(database_url=database_url)
    try:
        command.upgrade(alembic_cfg, _PARENT_REVISION)
        first_user_id, second_user_id = asyncio.run(_seed_existing_users(database_url=database_url))

        command.upgrade(alembic_cfg, _TARGET_REVISION)
        assert asyncio.run(_count_default_rows(database_url=database_url)) == 2
        assert (
            asyncio.run(_count_user_default_rows(database_url=database_url, user_id=first_user_id))
            == 1
        )
        assert (
            asyncio.run(_count_user_default_rows(database_url=database_url, user_id=second_user_id))
            == 1
        )

        command.upgrade(alembic_cfg, _TARGET_REVISION)
        assert asyncio.run(_count_default_rows(database_url=database_url)) == 2

        command.downgrade(alembic_cfg, _PARENT_REVISION)
        assert asyncio.run(_count_default_rows(database_url=database_url)) == 0

        command.upgrade(alembic_cfg, _TARGET_REVISION)
        assert asyncio.run(_count_default_rows(database_url=database_url)) == 2
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
