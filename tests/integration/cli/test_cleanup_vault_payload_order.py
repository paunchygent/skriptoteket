"""Payload files are deleted only after their group's rows commit, against PostgreSQL.

A failed row commit rolls the rows back and leaves every payload on disk. A failed
payload deletion after the commit leaves an orphaned file with its row gone, is logged,
and does not stop the purge from reaching the next group.
These are backend integration regressions, not browser proof.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from functools import partial
from pathlib import Path
from types import TracebackType
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from skriptoteket.cli.commands.cleanup_vault_files import (
    VaultCleanupScope,
    open_vault_cleanup_scope,
    purge_expired_vault_files,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.infrastructure.db.payload_guard_engine import PayloadGuardEngine
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
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
_TRASHED_AT = _CUTOFF - timedelta(days=1)


class _CommitFailsUow(SQLAlchemyUnitOfWork):
    """Roll the transaction back for real, as a failed COMMIT does, and raise."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        failure = RuntimeError("commit failed")
        await super().__aexit__(RuntimeError, failure, None)
        raise failure


async def _seed_group(
    factory: async_sessionmaker[AsyncSession], storage: LocalVaultStorage, *, lineage: bool
) -> tuple[UUID, list[VaultFile]]:
    async with factory() as session:
        owner = await _owner(session)
        if lineage:
            lineage_id = uuid4()
            rows = [
                _exam(owner, lineage_id=lineage_id, file_bytes=100, deleted_at=_TRASHED_AT),
                _export(
                    owner,
                    lineage_id=lineage_id,
                    export_format="qti",
                    file_bytes=10,
                    deleted_at=_TRASHED_AT,
                ),
            ]
        else:
            rows = [_file(owner, name="plain.pdf", file_bytes=5, deleted_at=_TRASHED_AT)]
        async with SQLAlchemyUnitOfWork(session):
            repo = PostgreSQLUserVaultFileRepository(
                session, unpooled_payload_guard_engine(session.bind)
            )
            for row in rows:
                await repo.create(file=row)
                await storage.store_file(user_id=owner, file_id=row.id, content=b"payload")
            await PostgreSQLUserVaultUsageRepository(session).upsert(
                usage=VaultUsage(user_id=owner, bytes_total=0, updated_at=_TRASHED_AT)
            )
    return owner, rows


@pytest.mark.parametrize("lineage", [False, True])
async def test_failed_row_commit_keeps_every_payload_and_row(
    session_factory: async_sessionmaker[AsyncSession],
    payload_guard_engine: PayloadGuardEngine,
    tmp_path: Path,
    lineage: bool,
) -> None:
    storage = LocalVaultStorage(vault_root=tmp_path)
    owner, rows = await _seed_group(session_factory, storage, lineage=lineage)

    @asynccontextmanager
    async def scope() -> AsyncIterator[VaultCleanupScope]:
        async with session_factory() as session:
            yield VaultCleanupScope(
                vault_files=PostgreSQLUserVaultFileRepository(
                    session, unpooled_payload_guard_engine(session.bind)
                ),
                vault_usage=PostgreSQLUserVaultUsageRepository(session),
                uow=_CommitFailsUow(session),
            )

    with pytest.raises(RuntimeError, match="commit failed"):
        await purge_expired_vault_files(
            scope_factory=scope, storage=storage, cutoff=_CUTOFF, now=_NOW
        )

    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        for row in rows:
            assert await repo.get_by_id(file_id=row.id) == row
            assert await storage.read_file(user_id=owner, file_id=row.id) == b"payload"

    # The failed group left nothing half-deleted, so a retry purges it completely.
    deleted, affected_users = await purge_expired_vault_files(
        scope_factory=partial(open_vault_cleanup_scope, session_factory, payload_guard_engine),
        storage=storage,
        cutoff=_CUTOFF,
        now=_NOW,
    )
    assert deleted == len(rows)
    assert affected_users == {owner}
    for row in rows:
        assert not await storage.exists_file(user_id=owner, file_id=row.id)


async def test_failed_payload_deletion_after_commit_is_logged_and_next_group_is_purged(
    session_factory: async_sessionmaker[AsyncSession],
    payload_guard_engine: PayloadGuardEngine,
    tmp_path: Path,
) -> None:
    class FailingStorage(LocalVaultStorage):
        def __init__(self, *, vault_root: Path, failing_file_id: UUID | None = None) -> None:
            super().__init__(vault_root=vault_root)
            self.failing_file_id = failing_file_id

        async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
            if file_id == self.failing_file_id:
                raise OSError("disk unavailable")
            await super().delete_file(user_id=user_id, file_id=file_id)

    storage = FailingStorage(vault_root=tmp_path)
    failing_owner, (failing_row,) = await _seed_group(session_factory, storage, lineage=False)
    next_owner, next_rows = await _seed_group(session_factory, storage, lineage=True)
    storage.failing_file_id = failing_row.id

    with capture_logs() as logs:
        deleted, affected_users = await purge_expired_vault_files(
            scope_factory=partial(open_vault_cleanup_scope, session_factory, payload_guard_engine),
            storage=storage,
            cutoff=_CUTOFF,
            now=_NOW,
        )

    assert deleted == 1 + len(next_rows)
    assert affected_users == {failing_owner, next_owner}
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        assert await repo.get_by_id(file_id=failing_row.id) is None
        # The orphaned payload stays on disk; no row points at a missing file.
        assert await storage.exists_file(user_id=failing_owner, file_id=failing_row.id)
        for row in next_rows:
            assert await repo.get_by_id(file_id=row.id) is None
            assert not await storage.exists_file(user_id=next_owner, file_id=row.id)
    failures = [entry for entry in logs if entry["event"] == "vault_cleanup_payload_delete_failed"]
    assert len(failures) == 1
    assert failures[0]["file_id"] == str(failing_row.id)
    assert failures[0]["user_id"] == str(failing_owner)
