"""Real PostgreSQL proof that the conversion phase and its start time reach the status.

The job queue, status handler and progress port are the production implementations; a
fixed clock stands in for the time the worker reports a phase at.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionPhase,
    OutlineQuestion,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import (
    SETTINGS,
    WORKER,
    ConversionWorld,
    Ids,
    batch,
)
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_LEASE = timedelta(minutes=15)


async def _queue_and_claim(
    session: AsyncSession, actor: User, world: ConversionWorld, now: datetime
) -> tuple[UUID, UUID]:
    queued = await ImportExamWorkspaceDocumentHandler(
        jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
        uow=SQLAlchemyUnitOfWork(session),
        clock=FixedClock(now),
        settings=SETTINGS,
        id_generator=Ids(),
    ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes", course_key=None)
    # The import queues the job already reading; the clock starts at the upload.
    assert (queued.phase, queued.phase_started_at) == (ConversionPhase.READING, now)
    stored_status = await world.status.handle(actor=actor, job_id=queued.job_id)
    assert (stored_status.phase, stored_status.phase_started_at) == (ConversionPhase.READING, now)
    async with world.uow:
        claimed = await world.jobs.claim_next(
            worker_id=WORKER,
            now=now,
            lease_ttl=_LEASE,
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        )
    assert claimed is not None
    # The worker's claim keeps the phase and its start time.
    assert (claimed.conversion_phase, claimed.conversion_phase_started_at) == (
        ConversionPhase.READING,
        now,
    )
    return queued.job_id, queued.lineage_id


async def test_each_phase_is_stored_with_the_clock_time_and_reaches_the_status(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        job_id, lineage_id = await _queue_and_claim(session, actor, world, now)

        for offset, phase in enumerate(ConversionPhase):
            reported_at = now + timedelta(seconds=offset + 1)
            reporting = ConversionWorld(session, storage, FixedClock(reported_at))
            await reporting.progress.phase(worker_id=WORKER, job_id=job_id, phase=phase)
            status = await world.status.handle(actor=actor, job_id=job_id)
            assert (status.phase, status.phase_started_at) == (phase, reported_at)

        # A progress write and the open document response keep the phase (locked view).
        await world.progress.outline(
            worker_id=WORKER,
            job_id=job_id,
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
            worker_id=WORKER, job_id=job_id, update=batch(lineage_id, q2=None, q3=None)
        )
        opened = await world.opened(actor, lineage_id)
        assert opened.conversion is not None
        assert opened.conversion.phase is ConversionPhase.CONVERTING
        assert opened.conversion.phase_started_at == now + timedelta(seconds=4)


async def test_a_stale_worker_phase_write_is_ignored(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        job_id, _ = await _queue_and_claim(session, actor, world, now)
        await world.progress.phase(worker_id=WORKER, job_id=job_id, phase=ConversionPhase.FINDING)

        await world.progress.phase(
            worker_id="stale-worker", job_id=job_id, phase=ConversionPhase.CONVERTING
        )
        # A lease that already expired no longer fences in its own worker either.
        late = ConversionWorld(session, storage, FixedClock(now + _LEASE + timedelta(seconds=1)))
        await late.progress.phase(worker_id=WORKER, job_id=job_id, phase=ConversionPhase.SORTING)

        status = await world.status.handle(actor=actor, job_id=job_id)
        assert (status.phase, status.phase_started_at) == (ConversionPhase.FINDING, now)


async def test_a_reclaimed_job_writes_its_phase_again_with_the_new_start_time(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, FixedClock(now))
        job_id, _ = await _queue_and_claim(session, actor, world, now)
        await world.progress.phase(worker_id=WORKER, job_id=job_id, phase=ConversionPhase.READING)

        reclaimed_at = now + _LEASE + timedelta(minutes=1)
        reclaiming = ConversionWorld(session, storage, FixedClock(reclaimed_at))
        # Other tests of this module leave expired running jobs behind; take them until ours.
        for _ in range(10):
            async with reclaiming.uow:
                reclaimed = await reclaiming.jobs.claim_next_expired(
                    worker_id="second-worker",
                    now=reclaimed_at,
                    lease_ttl=_LEASE,
                    source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
                )
            assert reclaimed is not None
            if reclaimed.id == job_id:
                break
        assert reclaimed is not None
        assert reclaimed.id == job_id and reclaimed.locked_by == "second-worker"

        # The first worker lost the lease; the second reports reading again.
        await reclaiming.progress.phase(
            worker_id=WORKER, job_id=job_id, phase=ConversionPhase.SORTING
        )
        stale = await world.status.handle(actor=actor, job_id=job_id)
        assert (stale.phase, stale.phase_started_at) == (ConversionPhase.READING, now)
        await reclaiming.progress.phase(
            worker_id="second-worker", job_id=job_id, phase=ConversionPhase.READING
        )
        status = await world.status.handle(actor=actor, job_id=job_id)
        assert (status.phase, status.phase_started_at) == (ConversionPhase.READING, reclaimed_at)
