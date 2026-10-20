"""Real PostgreSQL proof of exam-row retirement, storage cleanup and new uniqueness."""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_PARENT = "b7e4d2a9c610"
_REVISION = "4e9b7d1c6a02"


async def _seed_old_files(
    database_url: str, *, owner: UUID, lineage: UUID, file_ids: tuple[UUID, UUID, UUID]
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider) "
                    "VALUES (:id, :email, 'user', 'local')"
                ),
                {"id": owner, "email": f"migration-{owner}@example.test"},
            )
            for index, (file_id, size) in enumerate(zip(file_ids, (11, 13, 17), strict=True)):
                await connection.execute(
                    text(
                        "INSERT INTO user_vault_files "
                        "(id, user_id, name, bytes, source_kind, source_artifact_id, "
                        "document_lineage_id, document_version, deleted_at) "
                        "VALUES (:id, :owner, :name, :size, 'app_export', :artifact, "
                        ":lineage, :revision, CASE WHEN :retired THEN now() ELSE NULL END)"
                    ),
                    {
                        "id": file_id,
                        "owner": owner,
                        "name": f"file-{index}.zip",
                        "size": size,
                        "artifact": (
                            f"documents.conversion_hub:exam-workspace:{lineage}:v{index + 1}"
                            if index < 2
                            else "another.app:export"
                        ),
                        "lineage": lineage if index < 2 else None,
                        "revision": index + 1 if index < 2 else None,
                        "retired": index == 1,
                    },
                )
            await connection.execute(
                text("INSERT INTO user_vault_usage (user_id, bytes_total) VALUES (:owner, 28)"),
                {"owner": owner},
            )
    finally:
        await engine.dispose()


async def _assert_retirement_and_unique_exam(
    database_url: str, *, owner: UUID, lineage: UUID, remaining_file: UUID
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            remaining = await connection.execute(text("SELECT id FROM user_vault_files"))
            assert remaining.scalars().all() == [remaining_file]
            assert (
                await connection.scalar(
                    text("SELECT bytes_total FROM user_vault_usage WHERE user_id = :owner"),
                    {"owner": owner},
                )
                == 17
            )
            indexes = set(
                (
                    await connection.execute(
                        text(
                            "SELECT indexname FROM pg_indexes WHERE tablename = 'user_vault_files'"
                        )
                    )
                ).scalars()
            )
            assert "uq_user_vault_files_document_version" not in indexes
            assert {
                "uq_user_vault_files_document_exam",
                "uq_user_vault_files_document_export",
            } <= indexes
            assert await connection.scalar(text("SELECT count(*) FROM exam_workspace_history")) == 0
            insert = text(
                "INSERT INTO user_vault_files "
                "(id, user_id, name, bytes, source_kind, document_lineage_id, document_version, "
                "export_format) VALUES (:id, :owner, 'new.zip', 1, 'app_export', "
                ":lineage, 1, :format)"
            )
            await connection.execute(
                insert, {"id": uuid4(), "owner": owner, "lineage": lineage, "format": None}
            )
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert, {"id": uuid4(), "owner": owner, "lineage": lineage, "format": None}
                    )
            for export_format in ("qti", "pdf", "docx"):
                await connection.execute(
                    insert,
                    {"id": uuid4(), "owner": owner, "lineage": lineage, "format": export_format},
                )
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert, {"id": uuid4(), "owner": owner, "lineage": lineage, "format": "qti"}
                    )
            await connection.execute(
                text(
                    "UPDATE user_vault_files SET deleted_at = now() "
                    "WHERE user_id = :owner AND document_lineage_id = :lineage "
                    "AND export_format = 'qti'"
                ),
                {"owner": owner, "lineage": lineage},
            )
            # A trashed format still owns its identity; saving it revives that row.
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert, {"id": uuid4(), "owner": owner, "lineage": lineage, "format": "qti"}
                    )
    finally:
        await engine.dispose()


def test_exam_migration_drops_old_files_releases_active_bytes_and_enforces_one_file(
    fresh_database: PooledDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_url = fresh_database.url
    alembic_config = alembic_config_for(database_url=database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    command.upgrade(alembic_config, _PARENT)
    owner, lineage = uuid4(), uuid4()
    file_ids = (uuid4(), uuid4(), uuid4())
    asyncio.run(_seed_old_files(database_url, owner=owner, lineage=lineage, file_ids=file_ids))
    owner_directory = tmp_path / str(owner)
    owner_directory.mkdir()
    for file_id, size in zip(file_ids, (11, 13, 17), strict=True):
        (owner_directory / str(file_id)).write_bytes(b"x" * size)

    command.upgrade(alembic_config, _REVISION)
    command.upgrade(alembic_config, _REVISION)
    assert not (owner_directory / str(file_ids[0])).exists()
    assert not (owner_directory / str(file_ids[1])).exists()
    assert (owner_directory / str(file_ids[2])).read_bytes() == b"x" * 17
    asyncio.run(
        _assert_retirement_and_unique_exam(
            database_url, owner=owner, lineage=lineage, remaining_file=file_ids[2]
        )
    )
