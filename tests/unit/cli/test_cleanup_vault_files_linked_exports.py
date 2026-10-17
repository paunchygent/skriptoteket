"""The vault cleanup purges an exam's payloads and rows together.

The producer captures the expired rows of a document lineage before it deletes
anything, deletes every physical payload of that group before the first row, and leaves
the payload of an exam that is still active alone.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.cli.commands.cleanup_vault_files import (
    VaultCleanupScope,
    purge_expired_vault_files,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
_CUTOFF = _NOW - timedelta(days=30)


def _row(
    *,
    user_id: UUID,
    file_bytes: int = 100,
    lineage_id: UUID | None = None,
    export_format: str | None = None,
    deleted_at: datetime | None = None,
) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Prov.provdokument.zip",
        bytes=file_bytes,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_artifact_id=None,
        document_lineage_id=lineage_id,
        document_version=1 if lineage_id is not None else None,
        export_format=export_format,
        created_at=_NOW - timedelta(days=60),
        deleted_at=deleted_at,
    )


def _recording_repo(
    journal: list[str], *, rows: list[VaultFile], expired: list[VaultFile]
) -> AsyncMock:
    """A repository that expires one batch and drops rows as they are deleted."""

    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.list_expired.side_effect = [expired, []]
    stored: dict[UUID, VaultFile] = {file.id: file for file in rows}

    async def _list_exam_files(
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        include_deleted: bool,
    ) -> list[VaultFile]:
        return [
            file
            for file in stored.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and (include_deleted or file.deleted_at is None)
        ]

    async def _delete(*, file_id: UUID) -> None:
        journal.append(f"row:{file_id}")
        stored.pop(file_id, None)

    vault_files.list_exam_files.side_effect = _list_exam_files
    vault_files.delete.side_effect = _delete
    return vault_files


def _recording_storage(journal: list[str]) -> AsyncMock:
    storage = AsyncMock(spec=VaultStorageProtocol)

    async def _delete_file(*, user_id: UUID, file_id: UUID) -> None:
        journal.append(f"payload:{file_id}")

    storage.delete_file.side_effect = _delete_file
    return storage


def _recording_usage(journal: list[str]) -> AsyncMock:
    usage = AsyncMock(spec=VaultUsageRepositoryProtocol)

    async def _recompute_total(*, user_id: UUID, now: datetime) -> int:
        journal.append("recompute")
        return 0

    usage.recompute_total.side_effect = _recompute_total
    return usage


def _scope_factory(
    vault_files: VaultFileRepositoryProtocol, vault_usage: VaultUsageRepositoryProtocol
) -> Callable[[], AbstractAsyncContextManager[VaultCleanupScope]]:
    @asynccontextmanager
    async def scope() -> AsyncIterator[VaultCleanupScope]:
        yield VaultCleanupScope(
            vault_files=vault_files,
            vault_usage=vault_usage,
            uow=AsyncMock(spec=UnitOfWorkProtocol),
        )

    return scope


@pytest.mark.unit
@pytest.mark.asyncio
async def test_purge_deletes_every_payload_of_a_trashed_exam_before_any_row() -> None:
    owner = uuid4()
    lineage_id = uuid4()
    trashed_at = _CUTOFF - timedelta(days=1)
    exam = _row(user_id=owner, lineage_id=lineage_id, deleted_at=trashed_at)
    qti = _row(
        user_id=owner,
        file_bytes=10,
        lineage_id=lineage_id,
        export_format="qti",
        deleted_at=trashed_at,
    )
    pdf = _row(
        user_id=owner,
        file_bytes=20,
        lineage_id=lineage_id,
        export_format="pdf",
        deleted_at=trashed_at,
    )
    journal: list[str] = []
    all_rows = [exam, qti, pdf]
    vault_files = _recording_repo(journal, rows=all_rows, expired=all_rows)
    storage = _recording_storage(journal)
    # The trashed exam's bytes were released when it moved to the trash; the only byte
    # accounting of the purge is the recompute from the rows that remain, so released
    # bytes are never subtracted a second time.
    usage = _recording_usage(journal)

    deleted, affected_users = await purge_expired_vault_files(
        scope_factory=_scope_factory(vault_files, usage),
        storage=storage,
        cutoff=_CUTOFF,
        now=_NOW,
    )

    assert deleted == 3
    assert affected_users == {owner}
    assert journal == [
        f"payload:{exam.id}",
        f"payload:{qti.id}",
        f"payload:{pdf.id}",
        f"row:{exam.id}",
        f"row:{qti.id}",
        f"row:{pdf.id}",
        "recompute",
    ]
    usage.recompute_total.assert_awaited_once_with(user_id=owner, now=_NOW)
    usage.upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_purge_of_an_expired_exam_takes_every_export_whatever_its_state() -> None:
    owner = uuid4()
    lineage_id = uuid4()
    trashed_at = _CUTOFF - timedelta(days=1)
    exam = _row(user_id=owner, lineage_id=lineage_id, deleted_at=trashed_at)
    qti = _row(
        user_id=owner,
        file_bytes=10,
        lineage_id=lineage_id,
        export_format="qti",
        deleted_at=trashed_at,
    )
    # An export restored on its own while the exam sat in the trash is active again.
    orphan = _row(user_id=owner, file_bytes=30, lineage_id=lineage_id, export_format="docx")
    # An export trashed after the exam is still inside its own retention window.
    trashed_later = _row(
        user_id=owner,
        file_bytes=40,
        lineage_id=lineage_id,
        export_format="zip",
        deleted_at=_NOW - timedelta(days=5),
    )
    pinned = [exam, qti, orphan, trashed_later]
    journal: list[str] = []
    vault_files = _recording_repo(journal, rows=pinned, expired=[exam, qti])
    storage = _recording_storage(journal)

    deleted, affected_users = await purge_expired_vault_files(
        scope_factory=_scope_factory(vault_files, _recording_usage(journal)),
        storage=storage,
        cutoff=_CUTOFF,
        now=_NOW,
    )

    assert deleted == 4
    assert affected_users == {owner}
    payloads = [entry for entry in journal if entry.startswith("payload:")]
    rows = [entry for entry in journal if entry.startswith("row:")]
    assert set(payloads) == {f"payload:{file.id}" for file in pinned}
    assert set(rows) == {f"row:{file.id}" for file in pinned}
    assert max(journal.index(entry) for entry in payloads) < min(
        journal.index(entry) for entry in rows
    )
    assert journal[-1] == "recompute"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_purge_of_an_expired_export_leaves_the_live_exam_payload_and_row() -> None:
    owner = uuid4()
    lineage_id = uuid4()
    live_exam = _row(user_id=owner, lineage_id=lineage_id)
    expired_export = _row(
        user_id=owner,
        file_bytes=10,
        lineage_id=lineage_id,
        export_format="qti",
        deleted_at=_CUTOFF - timedelta(days=1),
    )
    journal: list[str] = []
    # The lineage group read returns the live exam as well; only the expired row may be
    # purged with the export.
    vault_files = _recording_repo(
        journal, rows=[live_exam, expired_export], expired=[expired_export]
    )
    storage = _recording_storage(journal)

    deleted, affected_users = await purge_expired_vault_files(
        scope_factory=_scope_factory(vault_files, _recording_usage(journal)),
        storage=storage,
        cutoff=_CUTOFF,
        now=_NOW,
    )

    assert deleted == 1
    assert affected_users == {owner}
    assert journal == [f"payload:{expired_export.id}", f"row:{expired_export.id}", "recompute"]
