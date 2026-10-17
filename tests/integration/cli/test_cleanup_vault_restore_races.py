"""Deterministic restore/expiry schedules against PostgreSQL and real vault payloads.

Fixed clocks model a restore request timestamp one second before retention ends
and cleanup one second after. They are contract inputs, not observed start times:
restore stays valid while cleanup selects the same row as expired. Events pause at
selection or payload deletion, never at elapsed-time guesses.
These are backend integration regressions, not browser proof.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.scripting.handlers.restore_vault_file import RestoreVaultFileHandler
from skriptoteket.application.scripting.vault import RestoreVaultFileCommand
from skriptoteket.cli.commands.cleanup_vault_files import (
    VaultCleanupScope,
    open_vault_cleanup_scope,
    purge_expired_vault_files,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.cli.test_cleanup_vault_files_linked_exports import (
    _CUTOFF,
    _NOW,
    _exam,
    _export,
    _file,
    _owner,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]
_RESTORE_NOW = _NOW - timedelta(seconds=2)
_TRASHED_AT = _CUTOFF - timedelta(seconds=1)


@asynccontextmanager
async def _scheduled_tasks() -> AsyncIterator[list[asyncio.Task[Any]]]:
    """Cancel and observe every actor even if a gate assertion or deadline fails."""
    tasks: list[asyncio.Task[Any]] = []
    try:
        yield tasks
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _seed(
    factory: async_sessionmaker[AsyncSession], storage: LocalVaultStorage, kind: str
) -> tuple[UUID, list[VaultFile], VaultFile]:
    async with factory() as session:
        owner = await _owner(session)
        lineage = uuid4()
        rows = (
            [_file(owner, name="plain.pdf", file_bytes=5, deleted_at=_TRASHED_AT)]
            if kind == "plain"
            else [
                _exam(owner, lineage_id=lineage, file_bytes=100, deleted_at=_TRASHED_AT),
                _export(
                    owner,
                    lineage_id=lineage,
                    export_format="qti",
                    file_bytes=10,
                    deleted_at=_TRASHED_AT,
                    trashed_with_exam=True,
                ),
            ]
        )
        async with SQLAlchemyUnitOfWork(session):
            repo = PostgreSQLUserVaultFileRepository(session)
            for row in rows:
                await repo.create(file=row)
                await storage.store_file(
                    user_id=owner, file_id=row.id, content=f"original:{row.id}".encode()
                )
            if kind != "plain":
                await repo.put_history(
                    user_id=owner, document_lineage_id=lineage, content=b"undo history"
                )
            await PostgreSQLUserVaultUsageRepository(session).upsert(
                usage=VaultUsage(user_id=owner, bytes_total=0, updated_at=_TRASHED_AT)
            )
        return owner, rows, rows[-1] if kind == "export" else rows[0]


def _restore(session: AsyncSession) -> RestoreVaultFileHandler:
    return RestoreVaultFileHandler(
        uow=SQLAlchemyUnitOfWork(session),
        vault_files=PostgreSQLUserVaultFileRepository(session),
        vault_usage=PostgreSQLUserVaultUsageRepository(session),
        settings=Settings.model_construct(VAULT_RETENTION_DAYS=30, VAULT_MAX_TOTAL_BYTES=10000),
        clock=FixedClock(_RESTORE_NOW),
    )


async def _assert_state(
    factory: async_sessionmaker[AsyncSession],
    storage: LocalVaultStorage,
    owner: UUID,
    rows: list[VaultFile],
    *,
    restored: bool,
) -> None:
    async with factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        for row in rows:
            actual = await repo.get_by_id(file_id=row.id)
            if restored:
                assert actual is not None and actual.deleted_at is None
                assert not actual.trashed_with_exam
                assert await storage.read_file(user_id=owner, file_id=row.id) == (
                    f"original:{row.id}".encode()
                )
            else:
                assert actual is None
                assert not await storage.exists_file(user_id=owner, file_id=row.id)
        lineage = rows[0].document_lineage_id
        if lineage is not None:
            assert await repo.get_history(user_id=owner, document_lineage_id=lineage) == (
                b"undo history" if restored else None
            )
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=owner)
        assert usage is not None
        assert usage.bytes_total == (sum(row.bytes for row in rows) if restored else 0)


@pytest.mark.parametrize("kind", ["plain", "exam", "export"])
async def test_restore_committed_after_expiry_selection_keeps_rows_and_original_payloads(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, kind: str
) -> None:
    storage = LocalVaultStorage(vault_root=tmp_path)
    owner, rows, target = await _seed(session_factory, storage, kind)
    selected, resume = asyncio.Event(), asyncio.Event()

    class PausedSelection(PostgreSQLUserVaultFileRepository):
        async def list_expired(self, *, cutoff: datetime, limit: int = 200) -> list[VaultFile]:
            result = await super().list_expired(cutoff=cutoff, limit=limit)
            if any(row.id == target.id for row in result):
                selected.set()
                await resume.wait()
            return result

    @asynccontextmanager
    async def scope() -> AsyncIterator[VaultCleanupScope]:
        async with session_factory() as session:
            yield VaultCleanupScope(
                vault_files=PausedSelection(session),
                vault_usage=PostgreSQLUserVaultUsageRepository(session),
                uow=SQLAlchemyUnitOfWork(session),
            )

    async with _scheduled_tasks() as tasks, asyncio.timeout(15):
        cleanup = asyncio.create_task(
            purge_expired_vault_files(
                scope_factory=scope, storage=storage, cutoff=_CUTOFF, now=_NOW
            )
        )
        tasks.append(cleanup)
        try:
            await selected.wait()
            async with session_factory() as session:
                result = await _restore(session).handle(
                    actor=make_user().model_copy(update={"id": owner}),
                    command=RestoreVaultFileCommand(file_id=target.id),
                )
                assert result.file.deleted_at is None
        finally:
            resume.set()
        deleted, _ = await cleanup
    assert deleted == 0
    await _assert_state(session_factory, storage, owner, rows, restored=True)


@pytest.mark.parametrize("kind", ["plain", "exam", "export"])
async def test_cleanup_winner_makes_waiting_restore_report_gone_not_half_restore(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, kind: str
) -> None:
    deleting, resume = asyncio.Event(), asyncio.Event()

    class PausedStorage(LocalVaultStorage):
        async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
            deleting.set()
            await resume.wait()
            await super().delete_file(user_id=user_id, file_id=file_id)

    storage = PausedStorage(vault_root=tmp_path)
    owner, rows, target = await _seed(session_factory, storage, kind)
    async with (
        session_factory() as restoring,
        _scheduled_tasks() as tasks,
        asyncio.timeout(15),
    ):
        # Keep this transaction open: the UoW joins and owns its commit/rollback.
        # Returning the connection to the pool would invalidate this observed PID.
        pid = await restoring.scalar(text("SELECT pg_backend_pid()"))
        cleanup = asyncio.create_task(
            purge_expired_vault_files(
                scope_factory=partial(open_vault_cleanup_scope, session_factory),
                storage=storage,
                cutoff=_CUTOFF,
                now=_NOW,
            )
        )
        tasks.append(cleanup)
        await deleting.wait()
        restore = asyncio.create_task(
            _restore(restoring).handle(
                actor=make_user().model_copy(update={"id": owner}),
                command=RestoreVaultFileCommand(file_id=target.id),
            )
        )
        tasks.append(restore)
        try:
            # SQL awaits yield to the competitor. Proceed only once PostgreSQL
            # observes contention or the unprotected implementation finishes.
            async with session_factory() as observer:
                while not restore.done():
                    if await observer.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                    ):
                        break
        finally:
            resume.set()
        deleted, _ = await cleanup
        outcome = (await asyncio.gather(restore, return_exceptions=True))[0]
    assert isinstance(outcome, DomainError), outcome
    assert outcome.code == ErrorCode.NOT_FOUND
    assert deleted == len(rows)
    await _assert_state(session_factory, storage, owner, rows, restored=False)


async def test_expiring_an_independently_trashed_export_preserves_live_exam_and_sibling(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    """L9 is directional: exporting/trashing one format never deletes its exam."""
    storage = LocalVaultStorage(vault_root=tmp_path)
    owner, (exam, expired), _ = await _seed(session_factory, storage, "exam")
    lineage = exam.document_lineage_id
    assert lineage is not None
    sibling = _export(owner, lineage_id=lineage, export_format="pdf", file_bytes=20)
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        repo = PostgreSQLUserVaultFileRepository(session)
        await repo.update(file=exam.model_copy(update={"deleted_at": None}))
        await repo.update(file=expired.model_copy(update={"trashed_with_exam": False}))
        await repo.create(file=sibling)
        await storage.store_file(user_id=owner, file_id=sibling.id, content=b"sibling PDF")
        await PostgreSQLUserVaultUsageRepository(session).upsert(
            usage=VaultUsage(user_id=owner, bytes_total=exam.bytes + sibling.bytes, updated_at=_NOW)
        )

    deleted, affected = await purge_expired_vault_files(
        scope_factory=partial(open_vault_cleanup_scope, session_factory),
        storage=storage,
        cutoff=_CUTOFF,
        now=_NOW,
    )

    assert deleted == 1 and affected == {owner}
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        assert await repo.get_by_id(file_id=expired.id) is None
        assert not await storage.exists_file(user_id=owner, file_id=expired.id)
        actual_exam = await repo.get_by_id(file_id=exam.id)
        assert actual_exam is not None and actual_exam.deleted_at is None
        assert await storage.read_file(user_id=owner, file_id=exam.id) == (
            f"original:{exam.id}".encode()
        )
        assert await repo.get_by_id(file_id=sibling.id) == sibling
        assert await storage.read_file(user_id=owner, file_id=sibling.id) == b"sibling PDF"
        assert await repo.get_history(user_id=owner, document_lineage_id=lineage) == b"undo history"
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=owner)
        assert usage is not None and usage.bytes_total == exam.bytes + sibling.bytes
