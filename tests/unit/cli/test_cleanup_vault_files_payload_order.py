"""A vault purge group deletes payload files only after its rows commit.

A failed row commit leaves every payload in place beside its surviving rows. A failed
payload deletion after the commit is logged with the file id and owner, leaves an
orphaned file, and never stops the purge from reaching the next group.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta
from types import TracebackType
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from skriptoteket.cli.commands.cleanup_vault_files import (
    VaultCleanupScope,
    purge_expired_vault_files,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol
from tests.unit.cli.test_cleanup_vault_files_linked_exports import (
    _CUTOFF,
    _NOW,
    _recording_repo,
    _recording_storage,
    _recording_usage,
    _row,
)


class _JournalUow:
    """A unit of work that journals its commit and can fail it."""

    def __init__(self, journal: list[str], *, fail_commit: bool = False) -> None:
        self._journal = journal
        self._fail_commit = fail_commit

    async def __aenter__(self) -> _JournalUow:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is not None:
            self._journal.append("rollback")
            return
        if self._fail_commit:
            self._journal.append("commit-failed")
            raise RuntimeError("commit failed")
        self._journal.append("commit")


def _scope_factory(
    vault_files: VaultFileRepositoryProtocol,
    vault_usage: AsyncMock,
    journal: list[str],
    *,
    fail_commit: bool = False,
) -> Callable[[], AbstractAsyncContextManager[VaultCleanupScope]]:
    @asynccontextmanager
    async def scope() -> AsyncIterator[VaultCleanupScope]:
        yield VaultCleanupScope(
            vault_files=vault_files,
            vault_usage=vault_usage,
            uow=_JournalUow(journal, fail_commit=fail_commit),
        )

    return scope


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payloads_are_deleted_only_after_the_group_commit() -> None:
    owner = uuid4()
    trashed_at = _CUTOFF - timedelta(days=1)
    plain = _row(user_id=owner, deleted_at=trashed_at)
    journal: list[str] = []
    vault_files = _recording_repo(journal, rows=[plain], expired=[plain])

    await purge_expired_vault_files(
        scope_factory=_scope_factory(vault_files, _recording_usage(journal), journal),
        storage=_recording_storage(journal),
        cutoff=_CUTOFF,
        now=_NOW,
    )

    assert journal == [f"row:{plain.id}", "recompute", "commit", f"payload:{plain.id}"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_row_commit_deletes_no_payload() -> None:
    owner = uuid4()
    lineage_id = uuid4()
    trashed_at = _CUTOFF - timedelta(days=1)
    exam = _row(user_id=owner, lineage_id=lineage_id, deleted_at=trashed_at)
    qti = _row(
        user_id=owner,
        lineage_id=lineage_id,
        export_format="qti",
        deleted_at=trashed_at,
    )
    journal: list[str] = []
    vault_files = _recording_repo(journal, rows=[exam, qti], expired=[exam, qti])
    storage = _recording_storage(journal)

    with pytest.raises(RuntimeError, match="commit failed"):
        await purge_expired_vault_files(
            scope_factory=_scope_factory(
                vault_files, _recording_usage(journal), journal, fail_commit=True
            ),
            storage=storage,
            cutoff=_CUTOFF,
            now=_NOW,
        )

    storage.delete_file.assert_not_awaited()
    assert not [entry for entry in journal if entry.startswith("payload:")]
    assert journal[-1] == "commit-failed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_payload_deletion_is_logged_and_the_next_group_is_still_purged() -> None:
    first_owner = uuid4()
    second_owner = uuid4()
    trashed_at = _CUTOFF - timedelta(days=1)
    failing = _row(user_id=first_owner, deleted_at=trashed_at)
    next_group = _row(user_id=second_owner, deleted_at=trashed_at)
    journal: list[str] = []
    vault_files = _recording_repo(
        journal, rows=[failing, next_group], expired=[failing, next_group]
    )
    storage = AsyncMock(spec=VaultStorageProtocol)

    async def _delete_file(*, user_id: UUID, file_id: UUID) -> None:
        if file_id == failing.id:
            raise OSError("disk unavailable")
        journal.append(f"payload:{file_id}")

    storage.delete_file.side_effect = _delete_file

    with capture_logs() as logs:
        deleted, affected_users = await purge_expired_vault_files(
            scope_factory=_scope_factory(vault_files, _recording_usage(journal), journal),
            storage=storage,
            cutoff=_CUTOFF,
            now=_NOW,
        )

    assert deleted == 2
    assert affected_users == {first_owner, second_owner}
    assert f"row:{failing.id}" in journal
    assert f"row:{next_group.id}" in journal
    assert f"payload:{next_group.id}" in journal
    failures = [entry for entry in logs if entry["event"] == "vault_cleanup_payload_delete_failed"]
    assert len(failures) == 1
    assert failures[0]["file_id"] == str(failing.id)
    assert failures[0]["user_id"] == str(first_owner)
    assert failures[0]["log_level"] == "error"
