"""Controlled interleavings through real handlers, UoWs and PostgreSQL.

Repository subclasses only pause reads or the pending insert. PostgreSQL's blocking-PID view
lets the same schedules exercise both unlocked and serialized implementations,
without assuming that a delayed task has reached a particular database query.
These are integration regressions, not live browser/application proof.
"""

import asyncio
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.rename_vault_file import RenameVaultFileHandler
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, RenameVaultFileCommand
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.protocols.vault import VaultStorageProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.test_vault_rename_repository import (
    _NOW,
    _file,
    _owner,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]


async def _seed(
    factory: async_sessionmaker[AsyncSession], *, lineage: UUID | None = None
) -> tuple[UUID, list[VaultFile]]:
    async with factory() as session:
        owner = await _owner(session)
        files = (
            [
                _file(
                    owner,
                    name="Original.provdokument.zip",
                    document_lineage_id=lineage,
                    document_version=1,
                    source_artifact_id=f"documents.conversion_hub:exam-workspace:{lineage}:v1",
                )
            ]
            if lineage is not None
            else [_file(owner, name="Left.pdf"), _file(owner, name="Right.pdf")]
        )
        for file in files:
            await PostgreSQLUserVaultFileRepository(session).create(file=file)
        await session.commit()
        return owner, files


async def _wait_for_progress_or_database_block(
    *,
    factory: async_sessionmaker[AsyncSession],
    pid: int,
    reached: asyncio.Event,
) -> None:
    """Release the first actor when the competitor progresses or reaches a DB lock."""
    async with asyncio.timeout(10), factory() as observer:
        while not reached.is_set():
            blocked = await observer.scalar(
                text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
            )
            if blocked:
                return
            await asyncio.sleep(0.01)


async def test_delete_with_stale_record_preserves_a_concurrently_committed_rename(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, (target, _) = await _seed(session_factory)
    actor = make_user().model_copy(update={"id": owner})
    read, resume = asyncio.Event(), asyncio.Event()

    class PausedDeleteRepository(PostgreSQLUserVaultFileRepository):
        async def update(self, *, file: VaultFile) -> VaultFile:
            read.set()
            await resume.wait()
            return await super().update(file=file)

    async with asyncio.timeout(10), session_factory() as deleting:
        pending = asyncio.create_task(
            DeleteVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(deleting),
                vault_files=PausedDeleteRepository(deleting),
                vault_usage=PostgreSQLUserVaultUsageRepository(deleting),
                clock=FixedClock(_NOW),
            ).handle(actor=actor, command=DeleteVaultFileCommand(file_id=target.id))
        )
        await read.wait()
        try:
            async with session_factory() as renaming:
                await RenameVaultFileHandler(
                    uow=SQLAlchemyUnitOfWork(renaming),
                    vault_files=PostgreSQLUserVaultFileRepository(renaming),
                ).handle(
                    actor=actor, command=RenameVaultFileCommand(file_id=target.id, stem="Renamed")
                )
        finally:
            resume.set()
        deleted = await pending
        assert deleted.file.name == "Renamed.pdf"
    async with session_factory() as checking:
        actual = await PostgreSQLUserVaultFileRepository(checking).get_by_id(file_id=target.id)
        assert actual is not None
        assert actual.name == "Renamed.pdf"
        assert actual.deleted_at == _NOW
        assert actual.model_dump(exclude={"name", "deleted_at"}) == target.model_dump(
            exclude={"name", "deleted_at"}
        )


async def test_delete_committed_after_rename_read_is_not_resurrected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, (target, _) = await _seed(session_factory)
    actor = make_user().model_copy(update={"id": owner})
    checked, resume = asyncio.Event(), asyncio.Event()

    class PausedRepository(PostgreSQLUserVaultFileRepository):
        async def name_in_use(
            self,
            *,
            user_id: UUID,
            name: str,
            exclude_lineage_id: UUID | None,
            exclude_file_id: UUID | None,
        ) -> bool:
            used = await super().name_in_use(
                user_id=user_id,
                name=name,
                exclude_lineage_id=exclude_lineage_id,
                exclude_file_id=exclude_file_id,
            )
            checked.set()
            await resume.wait()
            return used

    async with asyncio.timeout(10), session_factory() as session:
        pending = asyncio.create_task(
            RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(session), vault_files=PausedRepository(session)
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=target.id, stem="Renamed"))
        )
        try:
            await checked.wait()
            async with session_factory() as deletion:
                await PostgreSQLUserVaultFileRepository(deletion).update(
                    file=target.model_copy(update={"deleted_at": _NOW})
                )
                await deletion.commit()
        finally:
            resume.set()
        outcome = (await asyncio.gather(pending, return_exceptions=True))[0]
    async with session_factory() as verify:
        actual = await PostgreSQLUserVaultFileRepository(verify).get_by_id(file_id=target.id)
        assert actual is not None and actual.deleted_at == _NOW
        assert actual.name == target.name
    assert isinstance(outcome, DomainError) and outcome.code == ErrorCode.NOT_FOUND


async def test_competing_same_owner_renames_return_one_named_collision(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, (left, right) = await _seed(session_factory)
    actor = make_user().model_copy(update={"id": owner})
    first_checked, second_checked, resume = asyncio.Event(), asyncio.Event(), asyncio.Event()

    class PausedRepository(PostgreSQLUserVaultFileRepository):
        def __init__(self, session: AsyncSession, *, first: bool) -> None:
            super().__init__(session)
            self.first = first

        async def name_in_use(
            self,
            *,
            user_id: UUID,
            name: str,
            exclude_lineage_id: UUID | None,
            exclude_file_id: UUID | None,
        ) -> bool:
            used = await super().name_in_use(
                user_id=user_id,
                name=name,
                exclude_lineage_id=exclude_lineage_id,
                exclude_file_id=exclude_file_id,
            )
            (first_checked if self.first else second_checked).set()
            if self.first:
                await resume.wait()
            return used

    async with (
        asyncio.timeout(10),
        session_factory() as first_session,
        session_factory() as second_session,
    ):
        second_pid = await second_session.scalar(text("SELECT pg_backend_pid()"))
        first = asyncio.create_task(
            RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(first_session),
                vault_files=PausedRepository(first_session, first=True),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=left.id, stem="Same"))
        )
        await first_checked.wait()
        second = asyncio.create_task(
            RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(second_session),
                vault_files=PausedRepository(second_session, first=False),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=right.id, stem="Same"))
        )
        try:
            await _wait_for_progress_or_database_block(
                factory=session_factory, pid=second_pid, reached=second_checked
            )
        finally:
            resume.set()
        outcomes = await asyncio.gather(first, second, return_exceptions=True)
    assert not isinstance(outcomes[0], BaseException), outcomes
    errors = [outcome for outcome in outcomes if isinstance(outcome, DomainError)]
    assert len(errors) == 1, outcomes
    assert errors[0].code == ErrorCode.VALIDATION_ERROR
    assert errors[0].details["code"] == "vault_name_in_use"
    async with session_factory() as verify:
        repo = PostgreSQLUserVaultFileRepository(verify)
        actual = [await repo.get_by_id(file_id=file.id) for file in (left, right)]
        assert sum(file is not None and file.name == "Same.pdf" for file in actual) == 1


async def test_version_saved_during_lineage_rename_uses_authoritative_name(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lineage = uuid4()
    owner, (head,) = await _seed(session_factory, lineage=lineage)
    actor = make_user().model_copy(update={"id": owner})
    creating, resume, renamed = asyncio.Event(), asyncio.Event(), asyncio.Event()

    class PausedRepository(PostgreSQLUserVaultFileRepository):
        async def create(self, *, file: VaultFile) -> VaultFile:
            creating.set()
            await resume.wait()
            return await super().create(file=file)

    async with (
        asyncio.timeout(10),
        session_factory() as rename_session,
        session_factory() as writer_session,
    ):
        rename_pid = await rename_session.scalar(text("SELECT pg_backend_pid()"))
        store = ExamWorkspaceDocumentStore(
            vault_files=PausedRepository(writer_session),
            vault_usage=PostgreSQLUserVaultUsageRepository(writer_session),
            vault_storage=AsyncMock(spec=VaultStorageProtocol),
            uow=SQLAlchemyUnitOfWork(writer_session),
            clock=FixedClock(_NOW),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
            ),
        )

        async def save_version() -> VaultFile:
            version = await store.save_version(
                actor=actor,
                file_id=uuid4(),
                name=head.name,
                content=b"version container bytes",
                lineage_id=lineage,
                version=2,
            )
            return version

        async def rename_document() -> None:
            await RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(rename_session),
                vault_files=PostgreSQLUserVaultFileRepository(rename_session),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=head.id, stem="Renamed"))
            renamed.set()

        writer = asyncio.create_task(save_version())
        await creating.wait()
        rename = asyncio.create_task(rename_document())
        try:
            await _wait_for_progress_or_database_block(
                factory=session_factory, pid=rename_pid, reached=renamed
            )
        finally:
            resume.set()
        await asyncio.gather(rename, writer)
    async with session_factory() as verify:
        versions = await PostgreSQLUserVaultFileRepository(verify).list_lineage_versions(
            user_id=owner, document_lineage_id=lineage
        )
        assert {file.document_version for file in versions} == {1, 2}
        assert {file.name for file in versions} == {"Renamed.provdokument.zip"}
