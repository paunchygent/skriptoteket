"""Seed saved exams from vault rows alone and preserve metadata on repeated upgrades."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from tests.fixtures.database_fixtures import _to_async_database_url
from tests.integration.migration_idempotency_support import _alembic_config, _reset_public_schema

pytestmark = [pytest.mark.integration, pytest.mark.docker]
_REVISION = "d7e4b9a12c80"
_PARENT = "c8a1f7e42d90"
_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


async def _seed(database_url: str) -> tuple[UUID, UUID, UUID]:
    owner, lineage, head = uuid4(), uuid4(), uuid4()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO users "
                    "(id,email,password_hash,role,auth_provider,created_at,updated_at) "
                    "VALUES (:id,:email,'hash','user','local',:now,:now)"
                ),
                {"id": owner, "email": f"{owner}@example.test", "now": _NOW},
            )
            await conn.execute(
                text(
                    "INSERT INTO user_profiles (user_id,created_at,updated_at) "
                    "VALUES (:id,:now,:now)"
                ),
                {"id": owner, "now": _NOW},
            )
            insert = text(
                "INSERT INTO user_vault_files "
                "(id,user_id,name,bytes,source_kind,source_artifact_id,document_lineage_id,"
                "document_version,document_saved_at,export_format,created_at,deleted_at) "
                "VALUES (:id,:owner,:name,12,'app_export',:source,:lineage,:version,:now,"
                ":format,:now,:deleted)"
            )
            base = {
                "owner": owner,
                "lineage": lineage,
                "version": 3,
                "now": _NOW,
                "format": None,
                "deleted": None,
                "source": f"documents.conversion_hub:exam-workspace:{lineage}",
            }
            for values in (
                {**base, "id": head, "name": "Chapter.4.provdokument.zip"},
                {
                    **base,
                    "id": uuid4(),
                    "name": "Trashed newer.provdokument.zip",
                    "version": 99,
                    "deleted": _NOW,
                },
                {**base, "id": uuid4(), "name": "Export.zip", "format": "qti"},
                {
                    **base,
                    "id": uuid4(),
                    "name": "Ordinary.zip",
                    "lineage": uuid4(),
                    "source": "some.other.app:artifact",
                },
                {**base, "id": uuid4(), "name": "No lineage.zip", "lineage": None},
                {
                    **base,
                    "id": uuid4(),
                    "name": "Trashed only.provdokument.zip",
                    "lineage": uuid4(),
                    "deleted": _NOW,
                },
            ):
                await conn.execute(insert, values)
    finally:
        await engine.dispose()
    return owner, lineage, head


async def _assert_seed(
    database_url: str,
    owner: UUID,
    lineage: UUID,
    head: UUID,
    *,
    title: str = "Chapter.4",
    course: str | None = None,
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT lineage_id,head_vault_file_id,course_key,title,saved_at "
                            "FROM exam_index WHERE owner_user_id=:owner"
                        ),
                        {"owner": owner},
                    )
                )
                .mappings()
                .all()
            )
            assert len(rows) == 2  # Active head plus trashed-only exam for later restore.
            seeded = next(row for row in rows if row["lineage_id"] == lineage)
            assert seeded["head_vault_file_id"] == head
            assert seeded["title"] == title
            assert seeded["course_key"] == course
            assert seeded["saved_at"] == _NOW
            assert {row["title"] for row in rows} == {title, "Trashed only"}
            assert (
                await conn.scalar(
                    text("SELECT exam_list_ordering FROM user_profiles WHERE user_id=:owner"),
                    {"owner": owner},
                )
                == "course"
            )
    finally:
        await engine.dispose()


async def _enrich(database_url: str, owner: UUID, lineage: UUID) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE exam_index SET title='Teacher edited title',course_key='SVESVE01' "
                    "WHERE owner_user_id=:owner AND lineage_id=:lineage"
                ),
                {"owner": owner, "lineage": lineage},
            )
    finally:
        await engine.dispose()


def test_migration_d7e4b9a12c80_seeds_heads_without_containers_and_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    database_url = _to_async_database_url(postgres_container.get_connection_url())
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        asyncio.run(_reset_public_schema(database_url=database_url))
        config = _alembic_config(database_url=database_url)
        command.upgrade(config, _PARENT)
        owner, lineage, head = asyncio.run(_seed(database_url))
        command.upgrade(config, _REVISION)
        command.upgrade(config, _REVISION)
        asyncio.run(_assert_seed(database_url, owner, lineage, head))
        asyncio.run(_enrich(database_url, owner, lineage))
        # Re-run the actual upgrade body against existing schema/data, not just Alembic's no-op.
        command.stamp(config, _PARENT)
        command.upgrade(config, _REVISION)
        asyncio.run(
            _assert_seed(
                database_url, owner, lineage, head, title="Teacher edited title", course="SVESVE01"
            )
        )
        command.downgrade(config, _PARENT)
        command.upgrade(config, _REVISION)
        asyncio.run(_assert_seed(database_url, owner, lineage, head))
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        asyncio.run(_assert_seed(database_url, owner, lineage, head))
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
