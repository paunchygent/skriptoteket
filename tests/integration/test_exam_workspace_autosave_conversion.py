"""Autosaved teacher edits must not resurrect placeholders after a conversion batch."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeTextSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.docx_conversion_progress import ConversionOutline, OutlineQuestion
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import (
    SETTINGS,
    WORKER,
    ConversionWorld,
    Ids,
    batch,
)
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import body

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


def _texts(document: NativeExamDocument) -> list[str]:
    return [
        "".join(
            segment.text
            for segment in item.body[0].segments
            if isinstance(segment, NativeTextSegment)
        )
        for item in document.items
    ]


def _editor(world: ConversionWorld) -> SaveExamWorkspaceDocumentHandler:
    return SaveExamWorkspaceDocumentHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        id_generator=Ids(),
        jobs=world.jobs,
    )


async def test_autosave_retains_teacher_edit_and_receives_later_converted_questions(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        queued = await ImportExamWorkspaceDocumentHandler(
            jobs=world.jobs,
            uow=world.uow,
            clock=clock,
            settings=SETTINGS,
            id_generator=Ids(),
        ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes", course_key=None)
        async with world.uow:
            claimed = await world.jobs.claim_next(
                worker_id=WORKER,
                now=now,
                lease_ttl=timedelta(minutes=15),
                source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            )
        assert claimed is not None
        lineage = queued.lineage_id
        await world.progress.outline(
            worker_id=WORKER,
            job_id=queued.job_id,
            outline=ConversionOutline(
                title=None,
                questions=tuple(
                    OutlineQuestion(
                        question_id=q, position=i, anchors=(f"p{i + 1}",), source_text=q
                    )
                    for i, q in enumerate(("q1", "q2", "q3"))
                ),
            ),
        )
        await world.progress.batch_ready(
            worker_id=WORKER, job_id=queued.job_id, update=batch(lineage, q2=None, q3=None)
        )
        opened = await world.open(actor, lineage)
        changed_item = opened.items[0].model_copy(update={"body": body("Lärarens fråga ett")})
        await StoreExamWorkspaceUndoStepHandler(
            vault_files=world.vault_files,
            codec=world.codec,
            store=world.store,
            id_generator=Ids(),
            jobs=world.jobs,
        ).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=(
                    await _editor(world).history(actor=actor, lineage_id=lineage)
                ).cursor,
                document=opened.model_copy(
                    update={"revision": 2, "items": (changed_item, *opened.items[1:])}
                ),
            ),
        )
        before_history = await _editor(world).history(actor=actor, lineage_id=lineage)
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=batch(lineage, q2="Fråga två klar", q3="Fråga tre klar"),
        )
    async with session_factory() as session:
        reopened_world = ConversionWorld(session, storage, clock)
        reopened = await reopened_world.open(actor, lineage)
        assert _texts(reopened) == ["Lärarens fråga ett", "Fråga två klar", "Fråga tre klar"]
        history = await _editor(reopened_world).history(actor=actor, lineage_id=lineage)
        assert len(history.step_ids) == 1
        assert history.step_ids == before_history.step_ids
        assert history.baseline_step_id == before_history.baseline_step_id
        assert history.cursor != before_history.cursor
        undo = await _editor(reopened_world).history_step(
            actor=actor, lineage_id=lineage, step_id=history.baseline_step_id
        )
        assert _texts(undo.document) == ["Fråga ett", "Fråga två klar", "Fråga tre klar"]
