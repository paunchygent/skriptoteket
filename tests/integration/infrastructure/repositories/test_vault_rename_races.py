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

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryCursor,
    stored_step,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.rename_vault_file import RenameVaultFileHandler
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, RenameVaultFileCommand
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
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
from skriptoteket.protocols.vault import VaultStorageProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.test_vault_rename_repository import (
    _NOW,
    _file,
    _owner,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    placeholder,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]


def _seed_container(lineage: UUID) -> bytes:
    """The imported exam the baseline holds."""
    return ExamWorkspaceContainerCodec().build(
        content=ExamWorkspaceContainerContent(
            document=NativeExamDocument(
                document_id=lineage,
                revision=1,
                title="Original exam",
                items=(placeholder("p:1", "A question"),),
                origin=NativeExamDocumentOrigin(kind="created"),
            )
        )
    )


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
                    source_artifact_id=f"documents.conversion_hub:exam-workspace:{lineage}",
                )
            ]
            if lineage is not None
            else [_file(owner, name="Left.pdf"), _file(owner, name="Right.pdf")]
        )
        for file in files:
            await PostgreSQLUserVaultFileRepository(
                session, unpooled_payload_guard_engine(session.bind)
            ).create(file=file)
        if lineage is not None:
            # An exam file carries its undo history; an overwrite asserts it exists.
            container = ExamWorkspaceContainerCodec().parse(content=_seed_container(lineage))
            history_repo = PostgreSQLUserVaultFileRepository(
                session, unpooled_payload_guard_engine(session.bind)
            )
            await history_repo.upsert_history_head(
                user_id=owner,
                document_lineage_id=lineage,
                head=ExamWorkspaceHistoryCursor(
                    cursor=lineage, current_step_id=lineage, baseline_step_id=lineage
                ),
            )
            await history_repo.insert_history_step(
                user_id=owner,
                document_lineage_id=lineage,
                step=stored_step(
                    step_id=lineage,
                    position=0,
                    document=container.document,
                    notes=container.notes,
                ),
                assets_by_id=dict(container.assets_by_id),
            )
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


async def test_delete_with_stale_record_preserves_a_concurrently_committed_rename(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, (target, _) = await _seed(session_factory)
    actor = make_user().model_copy(update={"id": owner})
    read, resume = asyncio.Event(), asyncio.Event()

    class PausedDeleteRepository(PostgreSQLUserVaultFileRepository):
        async def lock_lifecycle_rows(
            self, *, user_id: UUID, file_id: UUID, document_lineage_id: UUID | None
        ) -> list[VaultFile]:
            read.set()
            await resume.wait()
            return await super().lock_lifecycle_rows(
                user_id=user_id, file_id=file_id, document_lineage_id=document_lineage_id
            )

    async with asyncio.timeout(10), session_factory() as deleting:
        pending = asyncio.create_task(
            DeleteVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(deleting),
                vault_files=PausedDeleteRepository(
                    deleting, unpooled_payload_guard_engine(deleting.bind)
                ),
                vault_usage=PostgreSQLUserVaultUsageRepository(deleting),
                clock=FixedClock(_NOW),
            ).handle(actor=actor, command=DeleteVaultFileCommand(file_id=target.id))
        )
        await read.wait()
        try:
            async with session_factory() as renaming:
                await RenameVaultFileHandler(
                    uow=SQLAlchemyUnitOfWork(renaming),
                    vault_files=PostgreSQLUserVaultFileRepository(
                        renaming, unpooled_payload_guard_engine(renaming.bind)
                    ),
                    index=PostgreSQLExamIndexRepository(renaming),
                ).handle(
                    actor=actor, command=RenameVaultFileCommand(file_id=target.id, stem="Renamed")
                )
        finally:
            resume.set()
        deleted = await pending
        assert deleted.file.name == "Renamed.pdf"
    async with session_factory() as checking:
        actual = await PostgreSQLUserVaultFileRepository(
            checking, unpooled_payload_guard_engine(checking.bind)
        ).get_by_id(file_id=target.id)
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
                uow=SQLAlchemyUnitOfWork(session),
                vault_files=PausedRepository(session, unpooled_payload_guard_engine(session.bind)),
                index=PostgreSQLExamIndexRepository(session),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=target.id, stem="Renamed"))
        )
        try:
            await checked.wait()
            async with session_factory() as deletion:
                await PostgreSQLUserVaultFileRepository(
                    deletion, unpooled_payload_guard_engine(deletion.bind)
                ).update(file=target.model_copy(update={"deleted_at": _NOW}))
                await deletion.commit()
        finally:
            resume.set()
        outcome = (await asyncio.gather(pending, return_exceptions=True))[0]
    async with session_factory() as verify:
        actual = await PostgreSQLUserVaultFileRepository(
            verify, unpooled_payload_guard_engine(verify.bind)
        ).get_by_id(file_id=target.id)
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
            super().__init__(session, unpooled_payload_guard_engine(session.bind))
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
                index=PostgreSQLExamIndexRepository(first_session),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=left.id, stem="Same"))
        )
        await first_checked.wait()
        second = asyncio.create_task(
            RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(second_session),
                vault_files=PausedRepository(second_session, first=False),
                index=PostgreSQLExamIndexRepository(second_session),
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
        repo = PostgreSQLUserVaultFileRepository(verify, unpooled_payload_guard_engine(verify.bind))
        actual = [await repo.get_by_id(file_id=file.id) for file in (left, right)]
        assert sum(file is not None and file.name == "Same.pdf" for file in actual) == 1


async def test_overwrite_saved_during_lineage_rename_keeps_the_authoritative_name(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lineage = uuid4()
    owner, (head,) = await _seed(session_factory, lineage=lineage)
    actor = make_user().model_copy(update={"id": owner})
    writing, resume, renamed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    codec = ExamWorkspaceContainerCodec()
    payload = codec.build(
        content=ExamWorkspaceContainerContent(
            document=NativeExamDocument(
                document_id=lineage,
                revision=2,
                title="Overwritten exam",
                items=(placeholder("p:1", "A question"),),
                origin=NativeExamDocumentOrigin(kind="created"),
            )
        )
    )

    class PausedRepository(PostgreSQLUserVaultFileRepository):
        async def overwrite(self, *, file: VaultFile) -> VaultFile:
            writing.set()
            await resume.wait()
            return await super().overwrite(file=file)

    async with (
        asyncio.timeout(10),
        session_factory() as rename_session,
        session_factory() as writer_session,
    ):
        rename_pid = await rename_session.scalar(text("SELECT pg_backend_pid()"))
        store = ExamWorkspaceDocumentStore(
            vault_files=PausedRepository(
                writer_session, unpooled_payload_guard_engine(writer_session.bind)
            ),
            vault_usage=PostgreSQLUserVaultUsageRepository(writer_session),
            vault_storage=AsyncMock(spec=VaultStorageProtocol),
            index=PostgreSQLExamIndexRepository(writer_session),
            codec=codec,
            uow=SQLAlchemyUnitOfWork(writer_session),
            clock=FixedClock(_NOW),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
            ),
        )

        async def save_overwrite() -> VaultFile:
            return await store.save(
                actor=actor,
                file_id=uuid4(),
                name=head.name,
                content=payload,
                lineage_id=lineage,
                version=2,
                expected_revision=1,
                preserve_editor_position=True,
            )

        async def rename_document() -> None:
            await RenameVaultFileHandler(
                uow=SQLAlchemyUnitOfWork(rename_session),
                vault_files=PostgreSQLUserVaultFileRepository(
                    rename_session, unpooled_payload_guard_engine(rename_session.bind)
                ),
                index=PostgreSQLExamIndexRepository(rename_session),
            ).handle(actor=actor, command=RenameVaultFileCommand(file_id=head.id, stem="Renamed"))
            renamed.set()

        writer = asyncio.create_task(save_overwrite())
        await writing.wait()
        rename = asyncio.create_task(rename_document())
        try:
            await _wait_for_progress_or_database_block(
                factory=session_factory, pid=rename_pid, reached=renamed
            )
        finally:
            resume.set()
        await asyncio.gather(rename, writer)
    async with session_factory() as verify:
        actual = await PostgreSQLUserVaultFileRepository(
            verify, unpooled_payload_guard_engine(verify.bind)
        ).get_document_head(user_id=owner, document_lineage_id=lineage)
        assert actual is not None
        assert actual.id == head.id
        assert actual.name == "Renamed.provdokument.zip"
        assert actual.document_version == 2


async def test_rename_response_joins_new_name_without_rewriting_saved_exam_metadata(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lineage = uuid4()
    owner, (head,) = await _seed(session_factory, lineage=lineage)
    entry = ExamIndexEntry(
        owner_user_id=owner,
        lineage_id=lineage,
        course_key="mathematics-1a",
        title="The content title, not a filename",
        saved_at=_NOW,
        head_vault_file_id=head.id,
        document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    )
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        await PostgreSQLExamIndexRepository(session).upsert(entry=entry)

    async with session_factory() as session:
        result = await RenameVaultFileHandler(
            uow=SQLAlchemyUnitOfWork(session),
            vault_files=PostgreSQLUserVaultFileRepository(
                session, unpooled_payload_guard_engine(session.bind)
            ),
            index=PostgreSQLExamIndexRepository(session),
        ).handle(
            actor=make_user().model_copy(update={"id": owner}),
            command=RenameVaultFileCommand(file_id=head.id, stem="A different filename"),
        )
    assert result.file.name == "A different filename.provdokument.zip"
    summary = result.exam_summary
    assert summary is not None
    assert summary.model_dump() == {
        "lineage_id": lineage,
        "vault_file_id": head.id,
        "name": result.file.name,
        "version": 1,
        "saved_at": _NOW,
        "title": entry.title,
        "course_key": entry.course_key,
    }
    async with session_factory() as session:
        saved = await PostgreSQLExamIndexRepository(session).get(
            owner_user_id=owner, lineage_id=lineage
        )
        assert saved is not None
        assert saved.name == result.file.name
        assert saved.model_dump(exclude={"name", "version"}) == entry.model_dump()
