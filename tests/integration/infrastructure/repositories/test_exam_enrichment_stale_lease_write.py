"""Real Postgres proof that a stale worker slot cannot overwrite a reclaimed job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    finish_enrichment_job,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
_REAPER_ERROR = "enrichment_worker_lease_expired"


def _expired_running_job() -> ExamAnswerKeyEnrichmentJob:
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.WORKSPACE,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="quiz.docx",
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        available_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
        locked_by="old:0",
        locked_until=_NOW - timedelta(seconds=1),
    )


async def test_stale_slot_cannot_overwrite_job_the_reaper_failed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    job = _expired_running_job()
    async with session_factory() as seed, seed.begin():
        await PostgreSQLExamAnswerKeyEnrichmentJobRepository(seed).create(job=job)

    async with session_factory() as old_slot, old_slot.begin():
        old_jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(old_slot)
        # The old slot has read its own lease inside its transaction; it keeps the
        # loaded row referenced, so its identity map still holds the old lease.
        held = await old_slot.get(ExamAnswerKeyEnrichmentJobModel, job.id)
        assert held is not None and held.locked_by == "old:0"
        read = ExamAnswerKeyEnrichmentJob.model_validate(held)

        # The reaper adopts the expired job and fail-closes it, committing first.
        async with session_factory() as reaper_session, reaper_session.begin():
            reaper = PostgreSQLExamAnswerKeyEnrichmentJobRepository(reaper_session)
            adopted = await reaper.claim_next_expired(
                worker_id="new:1",
                now=_NOW,
                lease_ttl=timedelta(minutes=1),
                source_kind=ExamAnswerKeySourceKind.WORKSPACE,
            )
            assert adopted is not None and adopted.id == job.id
            await reaper.update(
                job=finish_enrichment_job(
                    job=adopted,
                    status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    now=_NOW,
                    last_error=_REAPER_ERROR,
                ),
                expected_worker_id="new:1",
            )

        with pytest.raises(DomainError) as conflict:
            await old_jobs.update(
                job=finish_enrichment_job(
                    job=read, status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, now=_NOW
                ),
                expected_worker_id="old:0",
            )
        assert conflict.value.code is ErrorCode.CONFLICT

    assert held.status == ExamAnswerKeyEnrichmentJobStatus.FAILED.value  # row was refreshed
    async with session_factory() as verify:
        final = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(verify).get_by_id(
            job_id=job.id
        )
    assert final is not None
    assert final.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert final.last_error == _REAPER_ERROR


async def test_owning_slot_still_finalizes_its_own_lease(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    job = _expired_running_job().model_copy(update={"locked_until": _NOW + timedelta(minutes=1)})
    async with session_factory() as seed, seed.begin():
        await PostgreSQLExamAnswerKeyEnrichmentJobRepository(seed).create(job=job)

    async with session_factory() as owner, owner.begin():
        finished = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(owner).update(
            job=finish_enrichment_job(
                job=job, status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, now=_NOW
            ),
            expected_worker_id="old:0",
        )
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
