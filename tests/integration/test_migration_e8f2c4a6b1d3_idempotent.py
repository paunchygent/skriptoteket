"""Real PostgreSQL proof of per-step undo storage and the dropped history blob."""

import asyncio
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_PARENT = "c8e4f2a6d9b3"
_REVISION = "e8f2c4a6b1d3"


async def _seed_old_history(database_url: str, *, owner, lineage) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider) "
                    "VALUES (:id, :email, 'user', 'local')"
                ),
                {"id": owner, "email": f"step-storage-{owner}@example.test"},
            )
            await connection.execute(
                text(
                    "INSERT INTO user_vault_files "
                    "(id, user_id, name, bytes, source_kind, source_artifact_id, "
                    "document_lineage_id, document_version) "
                    "VALUES (:id, :owner, 'prov.provdokument.zip', 8, 'app_export', "
                    ":artifact, :lineage, 1)"
                ),
                {
                    "id": uuid4(),
                    "owner": owner,
                    "artifact": f"documents.conversion_hub:exam-workspace:{lineage}",
                    "lineage": lineage,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO exam_workspace_history (user_id, lineage_id, content) "
                    "VALUES (:owner, :lineage, :content)"
                ),
                {"owner": owner, "lineage": lineage, "content": b"old blob history"},
            )
    finally:
        await engine.dispose()


async def _columns(connection, table: str) -> dict[str, str]:
    rows = await connection.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = :table"
        ),
        {"table": table},
    )
    return {row[0]: row[1] for row in rows.all()}


async def _assert_step_storage(database_url: str, *, owner, lineage) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            assert await connection.scalar(text("SELECT count(*) FROM exam_workspace_history")) == 0
            history_columns = await _columns(connection, "exam_workspace_history")
            assert "content" not in history_columns
            assert history_columns["cursor"] == "NO"
            assert history_columns["current_step_id"] == "NO"
            assert history_columns["baseline_step_id"] == "NO"
            for table in ("exam_workspace_history_steps", "exam_workspace_history_assets"):
                tables = await connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_name = :table"
                    ),
                    {"table": table},
                )
                assert table in set(tables.scalars().all()), table
            step_columns = await _columns(connection, "exam_workspace_history_steps")
            assert set(step_columns) >= {
                "user_id",
                "lineage_id",
                "step_id",
                "position",
                "document",
                "asset_ids",
                "notes",
            }
            asset_columns = await _columns(connection, "exam_workspace_history_assets")
            assert set(asset_columns) >= {"user_id", "lineage_id", "asset_id", "content"}
            found = await connection.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = :table"),
                {"table": "exam_workspace_history_steps"},
            )
            indexes = set(found.scalars().all())
            assert "ix_exam_workspace_history_steps_order" in indexes
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM user_vault_files "
                        "WHERE user_id = :owner AND document_lineage_id = :lineage"
                    ),
                    {"owner": owner, "lineage": lineage},
                )
                == 1
            )
    finally:
        await engine.dispose()


def test_exam_step_storage_drops_the_blob_and_creates_per_step_tables(
    database_url: str, alembic_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(alembic_config, _PARENT)
    owner, lineage = uuid4(), uuid4()
    asyncio.run(_seed_old_history(database_url, owner=owner, lineage=lineage))

    command.upgrade(alembic_config, _REVISION)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_step_storage(database_url, owner=owner, lineage=lineage))

    command.downgrade(alembic_config, _PARENT)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_step_storage(database_url, owner=owner, lineage=lineage))
