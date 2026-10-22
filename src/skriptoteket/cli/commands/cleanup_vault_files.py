from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from uuid import UUID

import structlog
import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.payload_guard_engine import (
    PayloadGuardEngine,
    open_payload_guard_engine,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

_EXPIRED_BATCH_SIZE = 200

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class VaultCleanupScope:
    """Repositories and an unentered UoW belonging to one fresh session.

    A scope must not share an ambient transaction: releasing a SAVEPOINT does
    not release transaction-scoped advisory locks.
    """

    vault_files: VaultFileRepositoryProtocol
    vault_usage: VaultUsageRepositoryProtocol
    uow: UnitOfWorkProtocol


@asynccontextmanager
async def open_vault_cleanup_scope(
    session_factory: async_sessionmaker[AsyncSession],
    guard_engine: PayloadGuardEngine,
) -> AsyncIterator[VaultCleanupScope]:
    """Give each selection or purge its own application session and root UoW."""
    async with session_factory() as session:
        yield VaultCleanupScope(
            vault_files=PostgreSQLUserVaultFileRepository(session, guard_engine),
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            uow=SQLAlchemyUnitOfWork(session),
        )


def cleanup_vault_files() -> None:
    """Delete expired vault files past retention (cron-friendly)."""
    asyncio.run(_cleanup_vault_files_async())


async def purge_expired_vault_files(
    *,
    scope_factory: Callable[[], AbstractAsyncContextManager[VaultCleanupScope]],
    storage: VaultStorageProtocol,
    cutoff: datetime,
    now: datetime,
) -> tuple[int, set[UUID]]:
    """Purge expired files, including all saved exports when their exam expires.

    Every row in an expired exam's lineage is captured before deletion, regardless
    of each export's own state. A group deletes its rows and commits them first, then
    deletes its payload files under the same payload guard, so a failed commit never
    leaves a row without its file. A failed file deletion is logged and leaves an
    orphaned file; the purge continues. When only an export expires, the live exam and
    its non-expired files stay.

    Each purge group commits through its own root UoW before releasing its
    payload guard. No SQL lock survives into acquisition of the next guard,
    including across different lineages or owners. Selection scopes close
    before any purge begins; callers supply fresh scopes, not an enclosing UoW.
    A later failure leaves earlier groups committed and can be retried.

    Returns the number of deleted rows and the owners whose bytes were recomputed.
    """

    deleted = 0
    affected_users: set[UUID] = set()
    while True:
        processed_lineages: set[tuple[UUID, UUID]] = set()
        async with scope_factory() as selection:
            expired = await selection.vault_files.list_expired(
                cutoff=cutoff, limit=_EXPIRED_BATCH_SIZE
            )
        if not expired:
            break
        for item in expired:
            lineage_id = item.document_lineage_id
            key = (item.user_id, lineage_id) if lineage_id is not None else None
            if key is not None and key in processed_lineages:
                continue
            async with scope_factory() as scope:
                vault_files = scope.vault_files
                guard = (
                    vault_files.guard_document_payload(
                        user_id=item.user_id, document_lineage_id=lineage_id
                    )
                    if lineage_id is not None
                    else nullcontext()
                )
                async with guard:
                    async with scope.uow:
                        if lineage_id is not None:
                            await vault_files.lock_document_lineage(
                                user_id=item.user_id, document_lineage_id=lineage_id
                            )
                        group = await _purge_group(
                            vault_files=vault_files, item=item, cutoff=cutoff
                        )
                        for member in group:
                            await vault_files.delete(file_id=member.id)
                        if group:
                            # Lock before summing so another lineage's concurrent save
                            # cannot publish accounting between our sum and its update.
                            await scope.vault_usage.get_for_update(user_id=item.user_id, now=now)
                            await scope.vault_usage.recompute_total(user_id=item.user_id, now=now)
                    # The rows are committed; the guard still excludes payload readers.
                    await _delete_payloads(storage=storage, group=group)
                deleted += len(group)
                if group:
                    affected_users.add(item.user_id)
            if key is not None and group:
                processed_lineages.add(key)

    return deleted, affected_users


async def _delete_payloads(*, storage: VaultStorageProtocol, group: list[VaultFile]) -> None:
    """Delete committed rows' payloads; a failure leaves an orphaned file, never a row."""
    for member in group:
        try:
            await storage.delete_file(user_id=member.user_id, file_id=member.id)
        except Exception:
            logger.exception(
                "vault_cleanup_payload_delete_failed",
                file_id=str(member.id),
                user_id=str(member.user_id),
            )


async def _purge_group(
    *,
    vault_files: VaultFileRepositoryProtocol,
    item: VaultFile,
    cutoff: datetime,
) -> list[VaultFile]:
    """Return the rows to purge with one expired row.

    Permanently deleting an exam takes the whole exam aggregate with it: every row of its
    lineage, in whatever state one saved export happens to be, so no export row can
    outlive its exam while its payload is still on disk. An export whose exam is still
    active expires alone: only the trashed rows past the cutoff are purged, never a live
    exam or a format that still has time left. The item itself is one of the returned
    rows only while it is still expired under its row lock. An empty group means
    the selected row was restored, no longer expired, or already purged.
    """

    # Lineage locks (when present) precede these UUID-ordered row locks, and
    # usage locks follow them. Plain files use exactly the same row-lock route.
    # Never use the selection snapshot to decide lifecycle or delete payloads.
    members = await vault_files.lock_lifecycle_rows(
        user_id=item.user_id,
        file_id=item.id,
        document_lineage_id=item.document_lineage_id,
    )
    target = next((member for member in members if member.id == item.id), None)
    if target is None or target.deleted_at is None or target.deleted_at >= cutoff:
        return []
    if target.document_lineage_id is None:
        return [target]

    exam_document = next((member for member in members if member.export_format is None), None)
    exam_is_expired = (
        exam_document is not None
        and exam_document.deleted_at is not None
        and exam_document.deleted_at < cutoff
    )
    if exam_is_expired:
        return members

    return [
        member for member in members if member.deleted_at is not None and member.deleted_at < cutoff
    ]


async def _cleanup_vault_files_async() -> None:
    settings = Settings()
    if settings.VAULT_RETENTION_DAYS < 0:
        raise ValueError("VAULT_RETENTION_DAYS must be >= 0")

    clock = UTCClock()
    now = clock.now()
    cutoff = now - timedelta(days=settings.VAULT_RETENTION_DAYS)

    async with open_session(settings) as session, open_payload_guard_engine(settings) as guard:
        session_factory = async_sessionmaker(session.bind, expire_on_commit=False)
        deleted, _affected_users = await purge_expired_vault_files(
            scope_factory=partial(open_vault_cleanup_scope, session_factory, guard),
            storage=LocalVaultStorage(vault_root=settings.VAULT_ROOT),
            cutoff=cutoff,
            now=now,
        )

    typer.echo(f"Cleanup vault files complete: deleted={deleted}")
