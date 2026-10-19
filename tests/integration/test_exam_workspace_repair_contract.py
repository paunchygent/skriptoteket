"""Real PostgreSQL/filesystem regressions for save, abandonment and trash."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.exam_workspace import DocxExamChunkerProtocol
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import WORKER, ConversionWorld, Ids, batch
from tests.integration.exam_workspace_repair_support import editor, running_exam, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


async def test_each_stored_edit_advances_the_file_and_keeps_steps_in_order(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        document = await seed_exam(world, actor)
        lineage = document.document_id
        opened = await world.opened(actor, lineage)
        undo = StoreExamWorkspaceUndoStepHandler(
            vault_files=world.vault_files,
            codec=world.codec,
            store=world.store,
            jobs=world.jobs,
            id_generator=Ids(),
        )
        await undo.handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=opened.history_cursor,
                document=document.model_copy(update={"title": "Earlier stored edit"}),
            ),
        )
        before = await world.store.get_history(actor=actor, lineage_id=lineage)
        await world.teacher_save(actor, document.model_copy(update={"title": "Latest stored edit"}))
        after = await world.store.get_history(actor=actor, lineage_id=lineage)
        assert after.cursor != before.cursor
        assert after.baseline == before.baseline
        # The stored edit is the next step after the position; earlier steps stay untouched.
        assert after.steps[:-1] == before.steps
        assert len(after.steps) == len(before.steps) + 1
        assert after.current_step_id == after.steps[-1].step_id
        saved_step = world.codec.parse(content=after.steps[-1].content)
        assert saved_step.document.title == "Latest stored edit"
        # A stale cursor stores nothing and keeps the file.
        with pytest.raises(DomainError) as stale:
            await undo.handle(
                actor=actor,
                lineage_id=lineage,
                request=StoreExamWorkspaceUndoStepRequest(
                    expected_cursor=before.cursor,
                    document=document.model_copy(update={"title": "Stale edit"}),
                ),
            )
        assert stale.value.code is ErrorCode.CONFLICT
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        reopened = await world.opened(actor, lineage)
        assert reopened.document.title == "Latest stored edit"
        assert reopened.document.revision == 3
        old_step = await editor(world).history_step(
            actor=actor, lineage_id=lineage, step_id=before.steps[0].step_id
        )
        assert old_step.document.title == "Earlier stored edit"
        assert (await world.store.get_history(actor=actor, lineage_id=lineage)).steps[
            :-1
        ] == before.steps
        await StoreExamWorkspaceUndoStepHandler(
            vault_files=world.vault_files,
            codec=world.codec,
            store=world.store,
            jobs=world.jobs,
            id_generator=Ids(),
        ).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=reopened.history_cursor,
                document=reopened.document.model_copy(update={"title": "Later stored edit"}),
            ),
        )
    async with session_factory() as session:
        latest = await ConversionWorld(session, storage, clock).opened(actor, lineage)
        assert latest.document.title == "Later stored edit"
        assert latest.document.revision == 4


@pytest.mark.parametrize("delivery", ["batch", "final"])
async def test_conversion_delivery_after_trash_preserves_the_single_exam_and_history(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, delivery: str
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        job, lineage = await running_exam(world, actor, clock.now())
        opened = await world.opened(actor, lineage)
        before = await world.store.get_history(actor=actor, lineage_id=lineage)
        payload = await storage.read_file(user_id=actor.id, file_id=opened.summary.vault_file_id)
        await DeleteVaultFileHandler(
            uow=world.uow,
            vault_files=world.vault_files,
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            clock=clock,
        ).handle(actor=actor, command=DeleteVaultFileCommand(file_id=opened.summary.vault_file_id))
        update = batch(lineage, q2="Second ready", q3="Third ready")
        if delivery == "batch":
            await world.progress.batch_ready(worker_id=WORKER, job_id=job.id, update=update)
        else:
            await world.progress.publish_final(
                worker_id=WORKER,
                job_id=job.id,
                lineage_id=lineage,
                actor=actor,
                file_id=uuid4(),
                update=update,
                notes=(),
            )
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        members = await world.vault_files.list_exam_files(
            user_id=actor.id, document_lineage_id=lineage, include_deleted=True
        )
        assert len(members) == 1
        assert members[0].id == opened.summary.vault_file_id
        assert members[0].deleted_at is not None
        assert await world.store.get_history(actor=actor, lineage_id=lineage) == before
        assert await storage.read_file(user_id=actor.id, file_id=members[0].id) == payload


async def test_real_docx_failure_wrapper_rolls_back_abandonment_if_job_update_fails(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        job, lineage = await running_exam(world, actor, clock.now())
        opened = await world.opened(actor, lineage)
        before_history = await world.store.get_history(actor=actor, lineage_id=lineage)
        before_row = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage
        )
        before_usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
        before = await storage.read_file(user_id=actor.id, file_id=opened.summary.vault_file_id)
        # An actual DB failure AFTER abandon has returned, inside the real _fail wrapper.
        await session.execute(
            text("""
            CREATE FUNCTION u1r_refuse_failed_job() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.status = 'failed' THEN
                    RAISE EXCEPTION 'u1r injected failed-job update refusal';
                END IF;
                RETURN NEW;
            END $$
        """)
        )
        await session.execute(
            text("""
            CREATE TRIGGER u1r_refuse_failed_job BEFORE UPDATE
            ON exam_answer_key_enrichment_jobs
            FOR EACH ROW EXECUTE FUNCTION u1r_refuse_failed_job()
        """)
        )
        await session.commit()
        pipeline = AsyncMock(spec=DocxConversionPipeline)
        pipeline.convert.side_effect = RuntimeError("injected provider failure")
        chunker = Mock(spec=DocxExamChunkerProtocol)
        chunker.chunk.return_value = ()
        handler = ProcessExamWorkspaceDocxJobHandler(
            jobs=world.jobs,
            chunker=chunker,
            pipeline=pipeline,
            progress=world.progress,
            store=world.store,
            users=PostgreSQLUserRepository(session),
            uow=world.uow,
            clock=clock,
            id_generator=Ids(),
        )
        try:
            with pytest.raises(DBAPIError, match="u1r injected failed-job update refusal"):
                await handler.handle(job=job)
        finally:
            await session.rollback()
            await session.execute(
                text("DROP TRIGGER u1r_refuse_failed_job ON exam_answer_key_enrichment_jobs")
            )
            await session.execute(text("DROP FUNCTION u1r_refuse_failed_job()"))
            await session.commit()
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        row = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage
        )
        assert row is not None
        assert row == before_row
        assert (
            await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id) == before_usage
        )
        assert await storage.read_file(user_id=actor.id, file_id=row.id) == before
        assert await world.store.get_history(actor=actor, lineage_id=lineage) == before_history
        assert (await world.opened(actor, lineage)).document == opened.document
        unchanged_job = await world.jobs.get_by_id(job_id=job.id)
        assert unchanged_job is not None
        assert unchanged_job.status == job.status
