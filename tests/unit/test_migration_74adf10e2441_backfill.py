"""Focused fault-injection and failure-separation proof for the 74adf10e2441 backfill.

The docker integration test covers real files end to end through alembic. This
file loads the migration module directly from its path and drives
`_read_format_version` and `_backfill_format_versions` with injected seam
failures and stub connections.
"""

import importlib.util
import json
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import NoReturn
from uuid import uuid4

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "74adf10e2441_exam_index_document_format_version.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_74adf10e2441", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _CustomBoom(Exception):
    pass


def _write_valid_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "document.json", json.dumps({"schema_version": "native_exam_document_v10"})
        )


def _write_version_last_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "document.json",
            json.dumps({"padding": "x" * 4096, "schema_version": "native_exam_document_v10"}),
        )


def _read(migration, vault_root, head, *, owner="owner"):
    return migration._read_format_version(
        vault_root=vault_root, owner_user_id=owner, head_vault_file_id=head
    )


def test_version_last_in_object_still_versions(tmp_path: Path) -> None:
    migration = _load_migration()
    owner = tmp_path / "owner"
    owner.mkdir()
    head = str(uuid4())
    _write_version_last_zip(owner / head)
    assert _read(migration, tmp_path, head) == (10, "versioned")


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(_CustomBoom("S3CR3T-boom-marker"), id="custom"),
        pytest.param(MemoryError("S3CR3T-mem-marker"), id="memory"),
        pytest.param(RecursionError("S3CR3T-recursion-marker"), id="recursion"),
    ],
)
def test_file_read_seam_errors_become_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    migration = _load_migration()
    owner = tmp_path / "owner"
    owner.mkdir()
    head = str(uuid4())
    _write_valid_zip(owner / head)

    def _boom(*args: object, **kwargs: object) -> NoReturn:
        raise error

    monkeypatch.setattr(migration, "zipfile", SimpleNamespace(ZipFile=_boom))
    version, outcome = _read(migration, tmp_path, head)
    assert version == 0
    assert outcome == f"unreadable:{type(error).__name__}"
    assert "S3CR3T" not in outcome


def test_file_read_seam_cancellation_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    migration = _load_migration()
    owner = tmp_path / "owner"
    owner.mkdir()
    head = str(uuid4())
    _write_valid_zip(owner / head)

    def _cancel(*args: object, **kwargs: object) -> NoReturn:
        raise KeyboardInterrupt

    monkeypatch.setattr(migration, "zipfile", SimpleNamespace(ZipFile=_cancel))
    with pytest.raises(KeyboardInterrupt):
        _read(migration, tmp_path, head)


class _StubResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _StubConnection:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self.updates: list[dict[str, object]] = []
        self.update_error: Exception | None = None

    def execute(
        self, statement: object, parameters: dict[str, object] | None = None
    ) -> _StubResult:
        if "UPDATE" in str(statement):
            if self.update_error is not None:
                raise self.update_error
            assert parameters is not None
            self.updates.append(parameters)
            return _StubResult([])
        return _StubResult(self._rows)


def _row() -> SimpleNamespace:
    return SimpleNamespace(owner=str(uuid4()), lineage=str(uuid4()), head=str(uuid4()))


def test_missing_vault_root_raises_before_any_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    migration = _load_migration()
    missing = tmp_path / "no-such-vault"
    monkeypatch.setenv("VAULT_ROOT", str(missing))
    stub = _StubConnection([_row(), _row()])
    with pytest.raises(RuntimeError) as excinfo:
        migration._backfill_format_versions(connection=stub)
    assert str(missing) in str(excinfo.value)
    assert stub.updates == []


def test_empty_database_skips_vault_root_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    migration = _load_migration()
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path / "no-such-vault"))
    stub = _StubConnection([])
    migration._backfill_format_versions(connection=stub)
    assert stub.updates == []


def test_update_failure_escapes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _load_migration()
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    stub = _StubConnection([_row()])
    stub.update_error = RuntimeError("database down")
    with pytest.raises(RuntimeError, match="database down"):
        migration._backfill_format_versions(connection=stub)
