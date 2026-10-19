"""Real PostgreSQL proof of the edit lease columns next to the history head."""

import asyncio
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_PARENT = "e8f2c4a6b1d3"
_REVISION = "67c02402930c"

_LEASE_COLUMNS = (
    "lease_holder_tab_id",
    "lease_renewed_at",
    "lease_takeover_requested_by",
)


async def _seed_head(database_url: str, *, owner, lineage, cursor) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider) "
                    "VALUES (:id, :email, 'user', 'local')"
                ),
                {"id": owner, "email": f"edit-lease-{owner}@example.test"},
            )
            await connection.execute(
                text(
                    "INSERT INTO exam_workspace_history "
                    "(user_id, lineage_id, cursor, current_step_id, baseline_step_id) "
                    "VALUES (:owner, :lineage, :cursor, :cursor, :cursor)"
                ),
                {"owner": owner, "lineage": lineage, "cursor": cursor},
            )
    finally:
        await engine.dispose()


async def _assert_edit_lease(database_url: str, *, owner, lineage, cursor) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            rows = await connection.execute(
                text(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'exam_workspace_history'"
                )
            )
            columns = {row[0]: row[1] for row in rows.all()}
            for name in _LEASE_COLUMNS:
                assert columns[name] == "YES", name
            heads = (
                await connection.execute(
                    text(
                        "SELECT cursor, current_step_id, baseline_step_id, "
                        "lease_holder_tab_id, lease_renewed_at, "
                        "lease_takeover_requested_by "
                        "FROM exam_workspace_history "
                        "WHERE user_id = :owner AND lineage_id = :lineage"
                    ),
                    {"owner": owner, "lineage": lineage},
                )
            ).all()
            assert len(heads) == 1
            assert heads[0][0] == cursor
            assert heads[0][1] == cursor
            assert heads[0][2] == cursor
            assert heads[0][3] is None
            assert heads[0][4] is None
            assert heads[0][5] is None
    finally:
        await engine.dispose()


def test_exam_edit_lease_columns_land_nullable_and_keep_the_head(
    database_url: str, alembic_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(alembic_config, _PARENT)
    owner, lineage, cursor = uuid4(), uuid4(), uuid4()
    asyncio.run(_seed_head(database_url, owner=owner, lineage=lineage, cursor=cursor))

    command.upgrade(alembic_config, _REVISION)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_edit_lease(database_url, owner=owner, lineage=lineage, cursor=cursor))

    command.downgrade(alembic_config, _PARENT)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_edit_lease(database_url, owner=owner, lineage=lineage, cursor=cursor))
