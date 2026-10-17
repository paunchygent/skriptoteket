"""Migration proof against real PostgreSQL, including an existing profile."""

import asyncio
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _seed_existing_profile(database_url: str, user_id: UUID) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider) "
                    "VALUES (:id, :email, 'user', 'local')"
                ),
                {"id": user_id, "email": f"courses-{user_id}@example.test"},
            )
            await connection.execute(
                text("INSERT INTO user_profiles (user_id) VALUES (:id)"), {"id": user_id}
            )
    finally:
        await engine.dispose()


async def _assert_column_and_existing_default(database_url: str, user_id: UUID) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            schema = await connection.execute(
                text(
                    "SELECT data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'user_profiles' "
                    "AND column_name = 'exam_courses'"
                )
            )
            assert schema.one() == ("jsonb", "NO")
            stored = await connection.scalar(
                text("SELECT exam_courses FROM user_profiles WHERE user_id = :id"), {"id": user_id}
            )
            assert stored == {"school_forms": [], "course_keys": []}
    finally:
        await engine.dispose()


@pytest.mark.docker
def test_exam_courses_migration_backfills_existing_profile_and_reupgrade_is_safe(
    database_url: str,
    alembic_config: Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(alembic_config, "4e9b7d1c6a02")
    user_id = uuid4()
    asyncio.run(_seed_existing_profile(database_url, user_id))

    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")
    asyncio.run(_assert_column_and_existing_default(database_url, user_id))

    command.downgrade(alembic_config, "4e9b7d1c6a02")
    command.upgrade(alembic_config, "head")
    asyncio.run(_assert_column_and_existing_default(database_url, user_id))
