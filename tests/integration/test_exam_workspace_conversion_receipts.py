"""Receipt projection over real PostgreSQL jobs and the production progress adapter.

Provisional batches are synthetic; these tests do not establish streamed UI behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.identity.models import User
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

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_LEASE = timedelta(minutes=15)


async def _start(world: ConversionWorld, actor: User) -> tuple[UUID, UUID]:
    queued = await ImportExamWorkspaceDocumentHandler(
        jobs=world.jobs,
        uow=world.uow,
        clock=world.clock,
        settings=SETTINGS,
        id_generator=Ids(),
    ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes", course_key=None)
    async with world.uow:
        claimed = await world.jobs.claim_next(
            worker_id=WORKER,
            now=world.clock.now(),
            lease_ttl=_LEASE,
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        )
    assert claimed is not None and claimed.id == queued.job_id
    initial = await world.status.handle(actor=actor, job_id=queued.job_id)
    assert initial.questions_received == 0
    await world.progress.outline(
        worker_id=WORKER,
        job_id=queued.job_id,
        outline=ConversionOutline(
            title=None,
            questions=tuple(
                OutlineQuestion(question_id=q, position=i, anchors=(f"p{i + 1}",), source_text=q)
                for i, q in enumerate(("q1", "q2", "q3"))
            ),
        ),
    )
    return queued.job_id, queued.lineage_id


async def _first_save(world: ConversionWorld, actor: User, job_id: UUID, lineage_id: UUID) -> None:
    await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q1", "q1"))
    received = await world.status.handle(actor=actor, job_id=job_id)
    assert (received.questions_received, received.questions_total, received.questions_done) == (
        1,
        3,
        0,
    )
    assert received.state == "running"
    assert received.document_revision is None and received.units == () and received.summary is None
    await world.progress.batch_ready(
        worker_id=WORKER,
        job_id=job_id,
        update=batch(lineage_id, q2=None, q3=None),
        notes=(),
    )
    first = await world.status.handle(actor=actor, job_id=job_id)
    assert (first.questions_received, first.questions_done, first.document_revision) == (1, 1, 1)


async def test_receipt_survives_interleaved_first_batch_later_batch_and_final_publication(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    storage = LocalVaultStorage(vault_root=tmp_path)
    clock = FixedClock(datetime.now(UTC))
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        job_id, lineage_id = await _start(world, actor)
        await _first_save(world, actor, job_id, lineage_id)

    # A separate session observes persisted receipt; the next receipt changes only membership.
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        before = await world.status.handle(actor=actor, job_id=job_id)
        document = await world.open(actor, lineage_id)
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q2", "q1"))
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q2", "q2"))
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=())
        after = await world.status.handle(actor=actor, job_id=job_id)
        assert after.model_dump(exclude={"questions_received"}) == before.model_dump(
            exclude={"questions_received"}
        )
        assert after.questions_received == 2
        assert await world.open(actor, lineage_id) == document
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=job_id,
            update=batch(lineage_id, q2="Fråga två", q3=None),
            notes=(),
        )
        saved = await world.status.handle(actor=actor, job_id=job_id)
        assert (saved.questions_received, saved.questions_done, saved.document_revision) == (
            2,
            2,
            2,
        )
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q3",))
        all_received = await world.status.handle(actor=actor, job_id=job_id)
        assert (
            all_received.state,
            all_received.questions_done,
            all_received.questions_received,
        ) == ("running", 2, 3)
        assert all_received.document_revision == saved.document_revision
        assert all_received.units == saved.units
        await world.progress.publish_final(
            worker_id=WORKER,
            job_id=job_id,
            lineage_id=lineage_id,
            actor=actor,
            file_id=uuid4(),
            update=batch(lineage_id, q2="Fråga två", q3="Fråga tre"),
            notes=(),
        )
        final = await world.status.handle(actor=actor, job_id=job_id)
        assert (final.questions_received, final.questions_done, final.document_revision) == (
            3,
            3,
            3,
        )


async def test_receipt_uses_existing_worker_live_lease_and_terminal_fence(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        job_id, _ = await _start(world, actor)
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q1",))
        await world.progress.received(worker_id="stale", job_id=job_id, question_ids=("q2",))
        expired = ConversionWorld(session, storage, FixedClock(now + _LEASE))
        await expired.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q3",))
        status = await world.status.handle(actor=actor, job_id=job_id)
        assert status.questions_received == 1
        async with world.uow:
            job = await world.jobs.get_by_id_for_update(job_id=job_id)
            assert job is not None
            await world.jobs.update(
                job=finish_enrichment_job(
                    job=job, status=ExamAnswerKeyEnrichmentJobStatus.FAILED, now=now
                ).model_copy(update={"source_docx": None})
            )
        await world.progress.received(worker_id=WORKER, job_id=job_id, question_ids=("q2", "q3"))
        failed = await world.status.handle(actor=actor, job_id=job_id)
        assert failed.state == "failed" and failed.questions_received == 1
        assert (
            failed.document_revision is None and failed.questions_done == 0 and failed.units == ()
        )
