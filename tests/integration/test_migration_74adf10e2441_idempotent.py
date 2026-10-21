"""Real PostgreSQL proof of the exam_index format-version backfill."""

import asyncio
import hashlib
import json
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = [pytest.mark.integration, pytest.mark.docker]

_PARENT = "67c02402930c"
_REVISION = "74adf10e2441"

_SAMPLE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "exam_workspace"
    / "migration_74adf10e2441"
    / "native_exam_document_v10.json"
)


def _head_zip(path: Path, *, schema_version: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("document.json", json.dumps({"schema_version": schema_version}))


def _head_zip_deflated(path: Path, *, schema_version: str, padding_size: int) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "document.json",
            json.dumps({"schema_version": schema_version, "padding": " " * padding_size}),
        )


def _head_zip_raw(path: Path, *, content: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("document.json", content)


def _head_zip_bytes(path: Path, *, data: bytes) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("document.json", data)


def _head_zip_without_document(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("other.json", json.dumps({"schema_version": "native_exam_document_v10"}))


def _head_zip_version_last(path: Path, *, schema_version: str, padding_size: int) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "document.json",
            json.dumps({"padding": " " * padding_size, "schema_version": schema_version}),
        )


def _head_zip_trailing_whitespace(path: Path, *, whitespace_size: int) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("document.json", _SAMPLE.read_text() + " " * whitespace_size)


def _head_zip_corrupt_crc(path: Path, *, schema_version: str) -> None:
    _head_zip(path, schema_version=schema_version)
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("document.json")
        data_offset = info.header_offset + 30 + len(info.filename.encode("utf-8"))
    raw = bytearray(path.read_bytes())
    raw[data_offset + 2] ^= 0xFF
    path.write_bytes(bytes(raw))


async def _seed_index_rows(
    database_url: str,
    *,
    owner: UUID,
    lineages: tuple[UUID, ...],
    file_ids: tuple[UUID, ...],
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, role, auth_provider) "
                    "VALUES (:id, :email, 'user', 'local')"
                ),
                {"id": owner, "email": f"exam-index-backfill-{owner}@example.test"},
            )
            for lineage, file_id in zip(lineages, file_ids, strict=True):
                await connection.execute(
                    text(
                        "INSERT INTO user_vault_files "
                        "(id, user_id, name, bytes, source_kind, source_artifact_id, "
                        "document_lineage_id, document_version, document_saved_at) "
                        "VALUES (:id, :owner, :name, 10, 'app_export', :artifact, "
                        ":lineage, 1, now())"
                    ),
                    {
                        "id": file_id,
                        "owner": owner,
                        "name": "Exam.provdokument.zip",
                        "artifact": f"documents.conversion_hub:exam-workspace:{lineage}",
                        "lineage": lineage,
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO exam_index "
                        "(owner_user_id, lineage_id, course_key, title, saved_at, "
                        "head_vault_file_id) "
                        "VALUES (:owner, :lineage, NULL, :title, now(), :file)"
                    ),
                    {"owner": owner, "lineage": lineage, "title": str(lineage), "file": file_id},
                )
    finally:
        await engine.dispose()


async def _assert_backfilled(database_url: str, *, expected: dict[UUID, int]) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            rows = (
                await connection.execute(
                    text("SELECT lineage_id, document_format_version FROM exam_index")
                )
            ).all()
            assert {row[0]: row[1] for row in rows} == expected
            nullable = await connection.scalar(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'exam_index' "
                    "AND column_name = 'document_format_version'"
                )
            )
            assert nullable == "NO"
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            "INSERT INTO exam_index "
                            "(owner_user_id, lineage_id, title, saved_at, head_vault_file_id) "
                            "SELECT owner_user_id, :lineage, 'missing', now(), "
                            "head_vault_file_id FROM exam_index LIMIT 1"
                        ),
                        {"lineage": uuid4()},
                    )
    finally:
        await engine.dispose()


def test_exam_index_format_version_backfills_from_head_files(
    database_url: str, alembic_config: Config, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, _PARENT)
    owner = uuid4()
    lineages = tuple(uuid4() for _ in range(20))
    file_ids = tuple(uuid4() for _ in range(20))
    asyncio.run(_seed_index_rows(database_url, owner=owner, lineages=lineages, file_ids=file_ids))
    owner_directory = tmp_path / str(owner)
    owner_directory.mkdir()

    # Processing order follows owner/lineage, so sort the pairs to place a bad
    # file first and a good file right after it.
    order = sorted(range(len(lineages)), key=lambda index: lineages[index])
    by_position = [lineages[index] for index in order]
    files_by_position = [file_ids[index] for index in order]

    def path_at(position: int) -> Path:
        return owner_directory / str(files_by_position[position])

    # 0: not a zip, immediately followed by a good file: the backfill continues.
    path_at(0).write_bytes(b"not a zip")
    _head_zip(path_at(1), schema_version="native_exam_document_v10")
    # 2: missing file (nothing written).
    _head_zip_without_document(path_at(3))
    _head_zip_corrupt_crc(path_at(4), schema_version="native_exam_document_v10")
    _head_zip_bytes(path_at(5), data=b'{"schema_version": "\xff\xfe invalid"}')
    _head_zip_raw(
        path_at(6),
        content='{"schema_version": "native_exam_document_v10", "other": 1',
    )
    _head_zip_raw(path_at(7), content='{"title": "no version here"}')
    _head_zip_raw(path_at(8), content='{"schema_version": 10}')
    _head_zip_raw(path_at(9), content='{"schema_version": "v10"}')
    _head_zip(path_at(10), schema_version="native_exam_document_v" + "1" * 10)
    _head_zip(path_at(11), schema_version="native_exam_document_v" + "1" * 20)
    _head_zip_raw(
        path_at(12),
        content='{"schema_version":"native_exam_document_v10","other":' + "1" * 5000 + "}",
    )
    _head_zip_raw(path_at(13), content="[" * 200000 + "]" * 200000)
    _head_zip_raw(path_at(14), content='["not", "a", "dict"]')
    # Valid documents the backfill must version, however large or ordered.
    _head_zip_version_last(
        path_at(15), schema_version="native_exam_document_v10", padding_size=1024 * 1024
    )
    _head_zip_deflated(
        path_at(16),
        schema_version="native_exam_document_v10",
        padding_size=33 * 1024 * 1024,
    )
    _head_zip_trailing_whitespace(path_at(17), whitespace_size=33 * 1024 * 1024)
    _head_zip(path_at(18), schema_version="native_exam_document_v10")
    _head_zip(path_at(19), schema_version="native_exam_document_v9")

    expected = {
        by_position[0]: 0,
        by_position[1]: 10,
        by_position[2]: 0,
        by_position[3]: 0,
        by_position[4]: 0,
        by_position[5]: 0,
        by_position[6]: 0,
        by_position[7]: 0,
        by_position[8]: 0,
        by_position[9]: 0,
        by_position[10]: 0,
        by_position[11]: 0,
        by_position[12]: 0,
        by_position[13]: 0,
        by_position[14]: 0,
        by_position[15]: 10,
        by_position[16]: 10,
        by_position[17]: 10,
        by_position[18]: 10,
        by_position[19]: 9,
    }

    hashes_before = {
        position: hashlib.sha256(path_at(position).read_bytes()).hexdigest()
        for position in range(20)
        if position != 2
    }

    command.upgrade(alembic_config, _REVISION)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_backfilled(database_url, expected=expected))

    hashes_after = {
        position: hashlib.sha256(path_at(position).read_bytes()).hexdigest()
        for position in range(20)
        if position != 2
    }
    assert hashes_after == hashes_before

    command.downgrade(alembic_config, _PARENT)
    command.upgrade(alembic_config, _REVISION)
    asyncio.run(_assert_backfilled(database_url, expected=expected))
