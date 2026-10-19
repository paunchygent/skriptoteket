"""A failed COMMIT must not overwrite another request's committed export payload.

PostgreSQL, UoW, repositories, writers and filesystem are real. A deferred trigger
injects COMMIT failure and a storage-port barrier controls compensation scheduling.
The winner may correctly wait on a database guard, but cannot lose committed bytes.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_guest_draft_handoff import (
    ImportGuestExamDraftHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.repositories.exam_guest_draft_handoffs import (
    PostgreSQLExamGuestDraftHandoffRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld, Ids
from tests.integration.exam_workspace_repair_support import seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


class CompensationBarrierStorage(LocalVaultStorage):
    """Pause precisely the restoration of one export's original payload."""

    def __init__(self, *, vault_root: Path) -> None:
        super().__init__(vault_root=vault_root)
        self.original: bytes | None = None
        self.export_id: UUID | None = None
        self.restoring = asyncio.Event()
        self.resume = asyncio.Event()
        self.failed_session: AsyncSession | None = None
        self.writes = 0

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        if self.failed_session is not None and file_id == self.export_id:
            self.writes += 1
            if self.writes == 1:
                # Transaction-local injection cannot leak through the connection pool.
                await self.failed_session.execute(
                    text("SELECT set_config('u1r.fail_commit', 'yes', true)")
                )
            elif self.writes == 2:
                assert content == self.original
                self.restoring.set()
                await self.resume.wait()
        await super().store_file(user_id=user_id, file_id=file_id, content=content)


def exporter(world: ConversionWorld) -> ExportExamWorkspaceDocumentHandler:
    return ExportExamWorkspaceDocumentHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        renderer=ExamWorkspaceExportRenderer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
        ),
    )


async def winner_completed_or_waiting_on_database_guard(
    factory: async_sessionmaker[AsyncSession], winner: asyncio.Task[bytes]
) -> None:
    """Observe completion or a real lock wait, not an arbitrary scheduling delay."""
    async with asyncio.timeout(10), factory() as observer:
        while not winner.done():
            # This module owns its disposable Postgres; no unrelated requests run here.
            waiting = await observer.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_locks "
                    "WHERE locktype = 'advisory' AND NOT granted)"
                )
            )
            if waiting:
                return
            await asyncio.sleep(0.01)


async def test_failed_commit_compensation_never_overwrites_a_later_committed_export(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = CompensationBarrierStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        document = await seed_exam(world, actor)
        lineage = document.document_id
        exported = await exporter(world).save(
            actor=actor,
            lineage_id=lineage,
            target=ExamWorkspaceExportTarget.QTI,
            expected_revision=1,
        )
        storage.export_id = exported.id
        storage.original = await storage.read_file(user_id=actor.id, file_id=exported.id)
        await session.execute(
            text("""
            CREATE FUNCTION u1r_refuse_export_commit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF current_setting('u1r.fail_commit', true) = 'yes' THEN
                    RAISE EXCEPTION 'u1r injected COMMIT refusal';
                END IF;
                RETURN NEW;
            END $$
        """)
        )
        await session.execute(
            text("""
            CREATE CONSTRAINT TRIGGER u1r_refuse_export_commit
            AFTER UPDATE ON user_vault_files DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION u1r_refuse_export_commit()
        """)
        )
        await session.commit()

    async with session_factory() as failed_session:
        failed_world = ConversionWorld(
            failed_session, storage, FixedClock(clock.now() + timedelta(seconds=1))
        )
        storage.failed_session = failed_session

        async def failed_export() -> None:
            with pytest.raises(DBAPIError, match="u1r injected COMMIT refusal"):
                await exporter(failed_world).save(
                    actor=actor,
                    lineage_id=lineage,
                    target=ExamWorkspaceExportTarget.QTI,
                    expected_revision=1,
                )

        async def successful_save_and_export() -> bytes:
            async with session_factory() as session:
                winner_world = ConversionWorld(
                    session, LocalVaultStorage(vault_root=tmp_path), clock
                )
                await winner_world.teacher_save(
                    actor, document.model_copy(update={"title": "New committed exam and export"})
                )
                saved = await exporter(winner_world).save(
                    actor=actor,
                    lineage_id=lineage,
                    target=ExamWorkspaceExportTarget.QTI,
                    expected_revision=2,
                )
                assert saved.id == exported.id
                return await storage.read_file(user_id=actor.id, file_id=saved.id)

        failed = asyncio.create_task(failed_export())
        winner: asyncio.Task[bytes] | None = None
        try:
            await asyncio.wait_for(storage.restoring.wait(), timeout=10)
            winner = asyncio.create_task(successful_save_and_export())
            await winner_completed_or_waiting_on_database_guard(session_factory, winner)
        finally:
            storage.resume.set()
            await asyncio.wait_for(failed, timeout=10)
            await failed_session.rollback()
        assert winner is not None
        winning_bytes = await asyncio.wait_for(winner, timeout=10)
        assert winning_bytes != storage.original
    final_bytes = await storage.read_file(user_id=actor.id, file_id=exported.id)
    assert final_bytes == winning_bytes
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        members = await world.vault_files.list_exam_files(
            user_id=actor.id, document_lineage_id=lineage, include_deleted=True
        )
        assert len(members) == 2
        assert all(row.document_version == 2 for row in members)
        assert (
            await world.opened(actor, lineage)
        ).document.title == "New committed exam and export"


class HandoffCommitRefusalStorage(LocalVaultStorage):
    """Inject a COMMIT refusal from inside the handoff's payload write.

    The transaction-local flag is set on the failing session while the payload
    write runs, so the deferred trigger refuses the outermost COMMIT without
    leaking the flag to pooled sessions.
    """

    def __init__(self, *, vault_root: Path) -> None:
        super().__init__(vault_root=vault_root)
        self.failed_session: AsyncSession | None = None
        self.stored_ids: list[tuple[UUID, UUID]] = []
        self.deleted_ids: list[tuple[UUID, UUID]] = []

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        assert self.failed_session is not None
        if not self.stored_ids:
            await self.failed_session.execute(
                text("SELECT set_config('u4r.fail_commit', 'yes', true)")
            )
        self.stored_ids.append((user_id, file_id))
        await super().store_file(user_id=user_id, file_id=file_id, content=content)

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        self.deleted_ids.append((user_id, file_id))
        await super().delete_file(user_id=user_id, file_id=file_id)


def handoff_handler(
    world: ConversionWorld,
    clock: FixedClock,
    handoffs: PostgreSQLExamGuestDraftHandoffRepository,
) -> ImportGuestExamDraftHandler:
    return ImportGuestExamDraftHandler(
        handoffs=handoffs,
        reader=GetExamWorkspaceDocumentHandler(
            vault_files=world.vault_files,
            codec=world.codec,
            store=world.store,
            jobs=world.jobs,
            uow=world.uow,
        ),
        codec=world.codec,
        store=world.store,
        clock=clock,
        id_generator=Ids(),
        index=world.index,
    )


async def test_handoff_outer_commit_failure_compensates_the_written_payload(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = HandoffCommitRefusalStorage(vault_root=tmp_path)
    async with session_factory() as session:
        await session.execute(
            text("""
            CREATE FUNCTION u4r_refuse_handoff_commit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF current_setting('u4r.fail_commit', true) = 'yes' THEN
                    RAISE EXCEPTION 'u4r injected COMMIT refusal';
                END IF;
                RETURN NEW;
            END $$
        """)
        )
        await session.execute(
            text("""
            CREATE CONSTRAINT TRIGGER u4r_refuse_handoff_commit
            AFTER INSERT ON exam_guest_draft_handoffs DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION u4r_refuse_handoff_commit()
        """)
        )
        await session.commit()

    draft_id = uuid4()
    async with session_factory() as failed_session:
        failed_world = ConversionWorld(failed_session, storage, clock)
        storage.failed_session = failed_session
        handler = handoff_handler(
            failed_world, clock, PostgreSQLExamGuestDraftHandoffRepository(failed_session)
        )
        document = blank_native_exam_document().model_copy(update={"title": "Gästprov"})
        with pytest.raises(DBAPIError, match="u4r injected COMMIT refusal"):
            await handler.handle(
                actor=actor, draft_id=draft_id, document=document, assets_by_id={}, notes=()
            )
        await failed_session.rollback()

    assert storage.stored_ids != []
    assert storage.deleted_ids == storage.stored_ids
    async with session_factory() as session:
        assert (
            await PostgreSQLExamGuestDraftHandoffRepository(session).get_lineage(
                owner_user_id=actor.id, draft_id=draft_id
            )
            is None
        )
