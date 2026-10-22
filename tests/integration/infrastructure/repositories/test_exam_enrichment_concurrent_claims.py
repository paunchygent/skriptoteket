"""Real Postgres proof that concurrent enrichment slots never claim one job twice."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.workers.exam_answer_key_enrichment import (
    enrichment_slot_worker_id,
    process_next_answer_key_enrichment_job,
)
from tests.unit.workers.execution_queue_runtime_fakes import FakeClock

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
_TTL = timedelta(seconds=30)
_JOBS = 5
_CLAIMANTS = 2 * _JOBS


def _queued_job(*, index: int) -> ExamAnswerKeyEnrichmentJob:
    created = _NOW - timedelta(minutes=_JOBS - index)
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename=f"quiz-{index}.docx",
        source_docx=b"PK\x03\x04temporary-docx-bytes",
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        available_at=created,
        created_at=created,
        updated_at=created,
    )


async def _queue_jobs(*, db_session: AsyncSession) -> list[ExamAnswerKeyEnrichmentJob]:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    queued = [_queued_job(index=index) for index in range(_JOBS)]
    for job in queued:
        await jobs.create(job=job)
    await db_session.commit()
    return queued


async def test_concurrent_claim_next_hands_each_queued_job_to_exactly_one_worker(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    queued = await _queue_jobs(db_session=db_session)
    # Every claimant holds its transaction (and the row lock it won) until all
    # have tried to claim, so the surplus claimants contend with live locks.
    all_have_tried = asyncio.Barrier(_CLAIMANTS)

    async def claimant(slot: int) -> ExamAnswerKeyEnrichmentJob | None:
        async with session_factory() as session:
            async with session.begin():
                claimed = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).claim_next(
                    worker_id=f"worker:{slot}", now=_NOW, lease_ttl=_TTL
                )
                await all_have_tried.wait()
                return claimed

    outcomes = await asyncio.wait_for(
        asyncio.gather(*(claimant(slot) for slot in range(_CLAIMANTS))), timeout=30.0
    )

    claimed = [(slot, job) for slot, job in enumerate(outcomes) if job is not None]
    assert len(claimed) == _JOBS
    assert sum(1 for job in outcomes if job is None) == _CLAIMANTS - _JOBS
    assert sorted(job.id for _, job in claimed) == sorted(job.id for job in queued)
    assert all(job.locked_by == f"worker:{slot}" for slot, job in claimed)
    async with session_factory() as verify:
        rows = (await verify.execute(select(ExamAnswerKeyEnrichmentJobModel))).scalars().all()
    assert {row.id: row.locked_by for row in rows} == {job.id: job.locked_by for _, job in claimed}
    assert {row.status for row in rows} == {ExamAnswerKeyEnrichmentJobStatus.RUNNING.value}
    assert {row.attempts for row in rows} == {1}


class _RecordingHandler(ProcessExamAnswerKeyEnrichmentJobHandler):
    """Handler double: records each handled job and holds it until all slots overlap.

    It is a real handler subtype so the container registers it as the production type;
    it overrides both operations the worker lane calls and needs none of the real
    collaborators, so it does not run the base constructor.
    """

    def __init__(self, *, overlap: Callable[[], Awaitable[object]]) -> None:
        self.handled: list[tuple[UUID, str | None]] = []
        self._overlap = overlap

    async def fail_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        del worker_id, now, lease_ttl, source_kind
        return None

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        self.handled.append((job.id, job.locked_by))
        await self._overlap()
        return job.model_copy(
            update={"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, "source_docx": None}
        )


class _SlotProvider(Provider):
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        handler: _RecordingHandler,
    ) -> None:
        super().__init__()
        self._session_factory = session_factory
        self._handler = handler

    @provide(scope=Scope.REQUEST)
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def uow(self, session: AsyncSession) -> UnitOfWorkProtocol:
        return SQLAlchemyUnitOfWork(session)

    @provide(scope=Scope.REQUEST)
    def jobs(self, session: AsyncSession) -> ExamAnswerKeyEnrichmentJobRepositoryProtocol:
        return PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)

    @provide(scope=Scope.REQUEST)
    def handler(self) -> ProcessExamAnswerKeyEnrichmentJobHandler:
        return self._handler


async def test_concurrent_slots_handle_each_queued_job_exactly_once(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    queued = await _queue_jobs(db_session=db_session)
    # Held inside `handle`, so all job-owning slots are in flight at once.
    in_flight = asyncio.Barrier(_JOBS)
    handler = _RecordingHandler(overlap=in_flight.wait)
    container = make_async_container(
        _SlotProvider(session_factory=session_factory, handler=handler)
    )
    clock = FakeClock(now=_NOW)
    slot_ids = [
        enrichment_slot_worker_id(worker_id="worker", slot=slot) for slot in range(_CLAIMANTS)
    ]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *(
                    process_next_answer_key_enrichment_job(
                        container=container,
                        worker_id=slot_id,
                        now=_NOW,
                        lease_ttl=_TTL,
                        clock=clock,
                    )
                    for slot_id in slot_ids
                )
            ),
            timeout=30.0,
        )
    finally:
        await container.close()

    assert Counter(results) == {True: _JOBS, False: _CLAIMANTS - _JOBS}
    assert sorted(job_id for job_id, _ in handler.handled) == sorted(job.id for job in queued)
    handled_by = [worker_id for _, worker_id in handler.handled]
    assert len(set(handled_by)) == _JOBS
    assert set(handled_by) <= set(slot_ids)
