"""Cleanup must release lineage SQL locks before waiting for another payload.

Real handlers, PostgreSQL locks, UoWs and filesystem participate. The storage
barrier only arranges the reviewer's cleanup A / rename A / copy B interleaving.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.application.curated_apps.exam_workspace_history import (
    SaveAsExamWorkspaceDocumentRequest,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.rename_vault_file import RenameVaultFileHandler
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, RenameVaultFileCommand
from skriptoteket.cli.commands.cleanup_vault_files import (
    open_vault_cleanup_scope,
    purge_expired_vault_files,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld
from tests.integration.exam_workspace_repair_support import editor, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.integration.test_exam_workspace_payload_compensation import exporter

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


class PurgeBarrierStorage(LocalVaultStorage):
    """Stop at A's payload deletion, with its real lineage SQL lock held."""

    def __init__(self, *, vault_root: Path) -> None:
        super().__init__(vault_root=vault_root)
        self.paused_file_id: UUID | None = None
        self.deleting = asyncio.Event()
        self.resume = asyncio.Event()

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        if file_id == self.paused_file_id:
            self.deleting.set()
            await self.resume.wait()
        await super().delete_file(user_id=user_id, file_id=file_id)


async def observe_advisory_wait(factory: async_sessionmaker[AsyncSession], *, pid: int) -> None:
    """Wait for PostgreSQL's observed blocking edge, never a scheduling delay."""
    async with asyncio.timeout(10), factory() as observer:
        while True:
            blocked = await observer.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_locks "
                    "WHERE pid = :pid AND locktype = 'advisory' AND NOT granted)"
                ),
                {"pid": pid},
            )
            if blocked:
                print(f"Observed advisory-lock wait for backend {pid}")
                return


async def test_multilineage_cleanup_rename_and_save_as_complete_without_lock_cycle(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    now = datetime.now(UTC)
    actor = await create_owner(session_factory)
    storage = PurgeBarrierStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        first = await seed_exam(world, actor)
        second = await seed_exam(world, actor)
        first_head = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=first.document_id
        )
        assert first_head is not None
        expired_ids = []
        for index, document in enumerate((first, second)):
            exported = await exporter(world).save(
                actor=actor,
                lineage_id=document.document_id,
                target=ExamWorkspaceExportTarget.QTI,
                expected_revision=1,
            )
            expired_ids.append(exported.id)
            await DeleteVaultFileHandler(
                uow=world.uow,
                vault_files=world.vault_files,
                vault_usage=PostgreSQLUserVaultUsageRepository(session),
                clock=FixedClock(now - timedelta(days=60 - index)),
            ).handle(actor=actor, command=DeleteVaultFileCommand(file_id=exported.id))
        before_usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
        assert before_usage is not None

    storage.paused_file_id = expired_ids[0]
    rename_pid: asyncio.Future[int] = asyncio.get_running_loop().create_future()
    copy_pid: asyncio.Future[int] = asyncio.get_running_loop().create_future()

    async def cleanup() -> tuple[int, set[UUID]]:
        return await purge_expired_vault_files(
            scope_factory=partial(open_vault_cleanup_scope, session_factory),
            storage=storage,
            cutoff=now - timedelta(days=30),
            now=now,
        )

    async def rename() -> None:
        async with session_factory() as session:
            pid = await session.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            rename_pid.set_result(pid)
            await RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(session),
                vault_files=PostgreSQLUserVaultFileRepository(session),
                index=PostgreSQLExamIndexRepository(session),
            ).handle(
                actor=actor,
                command=RenameVaultFileCommand(file_id=first_head.id, stem="Renamed exam"),
            )

    async def copy() -> UUID:
        async with session_factory() as session:
            pid = await session.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            copy_pid.set_result(pid)
            world = ConversionWorld(session, storage, FixedClock(now))
            saved = await editor(world).save_as(
                actor=actor,
                lineage_id=second.document_id,
                request=SaveAsExamWorkspaceDocumentRequest(name="A separate copy", document=second),
            )
            return saved.document.document_id

    cleanup_task = asyncio.create_task(cleanup())
    tasks: list[asyncio.Task[object]] = [cleanup_task]
    try:
        async with asyncio.timeout(10):
            await storage.deleting.wait()
            rename_task = asyncio.create_task(rename())
            tasks.append(rename_task)
            await observe_advisory_wait(session_factory, pid=await rename_pid)
            copy_task = asyncio.create_task(copy())
            tasks.append(copy_task)
            await observe_advisory_wait(session_factory, pid=await copy_pid)
        storage.resume.set()
        # Deadline is a test hang safeguard, not a production timeout or timing assertion.
        async with asyncio.timeout(10):
            deleted, owners = await cleanup_task
            await rename_task
            copied_lineage = await copy_task
        assert deleted == 2
        assert owners == {actor.id}
    finally:
        storage.resume.set()
        for task in reversed(tasks):
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        assert (await world.opened(actor, first.document_id)).summary.name == (
            "Renamed exam.provdokument.zip"
        )
        assert (await world.opened(actor, second.document_id)).document == second
        copied = await world.opened(actor, copied_lineage)
        assert copied.document.document_id not in {first.document_id, second.document_id}
        assert copied.document.items == second.items
        assert copied.summary.name == "A separate copy.provdokument.zip"
        for file_id in expired_ids:
            assert await world.vault_files.get_by_id(file_id=file_id) is None
            assert not await storage.exists_file(user_id=actor.id, file_id=file_id)
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
        active = await world.vault_files.list_active_for_user(user_id=actor.id)
        assert len(active) == 3
        assert usage is not None
        assert usage.bytes_total == sum(row.bytes for row in active)
