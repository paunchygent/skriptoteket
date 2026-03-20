import os
import threading
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.database_fixtures import _to_async_database_url


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.asyncio
async def test_classroom_planner_migration_idempotency(postgres_container):
    """Verifies that the classroom planner migration is idempotent."""
    # Arrange
    database_url = _to_async_database_url(postgres_container.get_connection_url())
    os.environ["DATABASE_URL"] = database_url

    alembic_cfg = Config(str(Path("alembic.ini")))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    # Target revision for this story
    target_revision = "57a6ea32ef0a"
    # The revision before this one
    base_revision = "0032_user_file_vault"

    def run_alembic_cmd(cmd_func, *args):
        # Alembic commands are synchronous and might conflict with existing loops if not careful
        thread = threading.Thread(target=cmd_func, args=(alembic_cfg, *args))
        thread.start()
        thread.join()

    # We use async engine for verification
    async_url = _to_async_database_url(database_url)
    engine = create_async_engine(async_url)

    async def get_tables():
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return [row[0] for row in result.fetchall()]

    try:
        # Act & Assert

        # 1. Upgrade to target
        run_alembic_cmd(command.upgrade, target_revision)

        # Verify tables exist
        tables = await get_tables()
        assert "classroom_planner_rosters" in tables
        assert "classroom_planner_room_templates" in tables

        # 2. Downgrade to base
        run_alembic_cmd(command.downgrade, base_revision)

        # Verify tables are gone
        tables = await get_tables()
        assert "classroom_planner_rosters" not in tables
        assert "classroom_planner_room_templates" not in tables

        # 3. Re-upgrade to target
        run_alembic_cmd(command.upgrade, target_revision)

        # Verify tables exist again
        tables = await get_tables()
        assert "classroom_planner_rosters" in tables
        assert "classroom_planner_room_templates" in tables
    finally:
        await engine.dispose()
