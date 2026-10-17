"""Production stack setup for adversarial persistence repair contracts."""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ImportExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.docx_conversion_progress import ConversionOutline, OutlineQuestion
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import (
    SETTINGS,
    WORKER,
    ConversionWorld,
    Ids,
    batch,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import _reviewed


def editor(world: ConversionWorld) -> SaveExamWorkspaceDocumentHandler:
    return SaveExamWorkspaceDocumentHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        id_generator=Ids(),
        jobs=world.jobs,
    )


async def seed_exam(world: ConversionWorld, actor: User) -> NativeExamDocument:
    document = _reviewed(
        NativeExamDocument.model_validate_json(
            Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json").read_bytes()
        )
    ).model_copy(update={"document_id": uuid4(), "revision": 1})
    await world.store.save(
        actor=actor,
        file_id=uuid4(),
        name="Prov.provdokument.zip",
        content=world.codec.build(
            content=ExamWorkspaceContainerContent(document=document, assets_by_id={})
        ),
        lineage_id=document.document_id,
        version=1,
    )
    return document


async def running_exam(
    world: ConversionWorld, actor: User, now: datetime
) -> tuple[ExamAnswerKeyEnrichmentJob, UUID]:
    queued = await ImportExamWorkspaceDocumentHandler(
        jobs=world.jobs,
        uow=world.uow,
        clock=FixedClock(now),
        settings=SETTINGS,
        id_generator=Ids(),
    ).handle(
        actor=actor, filename="prov.docx", content=b"synthetic-conversion-input", course_key=None
    )
    async with world.uow:
        job = await world.jobs.claim_next(
            worker_id=WORKER,
            now=now,
            lease_ttl=timedelta(minutes=15),
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        )
    assert job is not None and job.id == queued.job_id
    await world.progress.outline(
        worker_id=WORKER,
        job_id=job.id,
        outline=ConversionOutline(
            title=None,
            questions=tuple(
                OutlineQuestion(question_id=q, position=i, anchors=(f"p{i + 1}",), source_text=q)
                for i, q in enumerate(("q1", "q2", "q3"))
            ),
        ),
    )
    await world.progress.batch_ready(
        worker_id=WORKER, job_id=job.id, update=batch(queued.lineage_id, q2=None, q3=None)
    )
    return job, queued.lineage_id
