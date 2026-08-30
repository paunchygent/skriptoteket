"""Concurrent PostgreSQL coverage for native Exam Converter ownership seams."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    enqueue_enrichment_job,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.public_exam_converter_job import (
    PublicExamConverterJobModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_converter_correction_sessions import (
    PostgreSQLExamConverterCorrectionSessionRepository,
)
from skriptoteket.infrastructure.repositories.public_exam_converter_jobs import (
    PostgreSQLPublicExamConverterJobRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]


async def _create_owner(
    session_factory: async_sessionmaker[AsyncSession],
) -> UUID:
    owner_id = uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        session.add(
            UserModel(
                id=owner_id,
                email=f"exam-concurrency-{owner_id}@example.test",
                password_hash="hash",
                role=Role.USER,
                auth_provider=AuthProvider.LOCAL,
                created_at=now,
                updated_at=now,
            )
        )
    return owner_id


def _candidate(*, owner_id: UUID, submission_key: str) -> ConversionHubJob:
    now = datetime.now(UTC)
    return ConversionHubJob(
        id=uuid4(),
        owner_user_id=owner_id,
        input_filename="exam.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        status=ConversionHubJobStatus.SUBMITTED,
        submission_idempotency_key=submission_key,
        created_at=now,
        updated_at=now,
    )


async def _acquire(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    candidate: ConversionHubJob,
) -> tuple[ConversionHubJob, bool]:
    async with session_factory() as session, session.begin():
        repository = PostgreSQLConversionHubJobRepository(session)
        return await repository.acquire_by_owner_and_submission_key(job=candidate)


async def test_identical_submissions_atomically_return_one_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id = await _create_owner(session_factory)
    submission_key = f"same-submit-{uuid4()}"

    first, second = await asyncio.gather(
        _acquire(
            session_factory=session_factory,
            candidate=_candidate(owner_id=owner_id, submission_key=submission_key),
        ),
        _acquire(
            session_factory=session_factory,
            candidate=_candidate(owner_id=owner_id, submission_key=submission_key),
        ),
    )

    assert first[0].id == second[0].id
    assert sorted((first[1], second[1])) == [False, True]
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ConversionHubJobModel)
            .where(
                ConversionHubJobModel.owner_user_id == owner_id,
                ConversionHubJobModel.submission_idempotency_key == submission_key,
            )
        )
    assert count == 1


async def test_concurrent_submissions_after_failure_atomically_acquire_one_fresh_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id = await _create_owner(session_factory)
    submission_key = f"failed-submit-{uuid4()}"
    failed, _ = await _acquire(
        session_factory=session_factory,
        candidate=_candidate(owner_id=owner_id, submission_key=submission_key),
    )
    async with session_factory() as session, session.begin():
        repository = PostgreSQLConversionHubJobRepository(session)
        await repository.update(
            job=failed.model_copy(
                update={
                    "status": ConversionHubJobStatus.FAILED,
                    "error_message": "conversion failed",
                }
            )
        )

    first, second = await asyncio.gather(
        _acquire(
            session_factory=session_factory,
            candidate=_candidate(owner_id=owner_id, submission_key=submission_key),
        ),
        _acquire(
            session_factory=session_factory,
            candidate=_candidate(owner_id=owner_id, submission_key=submission_key),
        ),
    )

    assert first[0].id == second[0].id
    assert first[0].id != failed.id
    assert sorted((first[1], second[1])) == [False, True]
    async with session_factory() as session:
        rows = (
            await session.scalars(
                select(ConversionHubJobModel)
                .where(ConversionHubJobModel.owner_user_id == owner_id)
                .order_by(ConversionHubJobModel.created_at)
            )
        ).all()
    assert len(rows) == 2
    assert rows[0].status == ConversionHubJobStatus.FAILED
    assert rows[0].submission_idempotency_key is None
    assert rows[1].submission_idempotency_key == submission_key


async def test_parent_job_lock_serializes_first_correction_and_publication(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id = await _create_owner(session_factory)
    candidate = _candidate(owner_id=owner_id, submission_key=f"lock-job-{uuid4()}")
    stored, _ = await _acquire(session_factory=session_factory, candidate=candidate)
    first_locked = asyncio.Event()
    release_first = asyncio.Event()
    second_locked = asyncio.Event()

    async def hold_first_lock() -> None:
        async with session_factory() as session, session.begin():
            repository = PostgreSQLExamConverterCorrectionSessionRepository(session)
            await repository.lock_owned_job(
                owner_user_id=owner_id,
                conversion_hub_job_id=stored.id,
            )
            first_locked.set()
            await release_first.wait()

    async def acquire_second_lock() -> None:
        await first_locked.wait()
        async with session_factory() as session, session.begin():
            repository = PostgreSQLExamConverterCorrectionSessionRepository(session)
            await repository.lock_owned_job(
                owner_user_id=owner_id,
                conversion_hub_job_id=stored.id,
            )
            second_locked.set()

    first_task = asyncio.create_task(hold_first_lock())
    second_task = asyncio.create_task(acquire_second_lock())
    await first_locked.wait()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(second_locked.wait(), timeout=0.1)
    release_first.set()
    await asyncio.gather(first_task, second_task)
    assert second_locked.is_set()


def _public_candidate(*, now: datetime) -> PublicExamConverterSubmittedJob:
    job_id = uuid4()
    return PublicExamConverterSubmittedJob(
        public_job_id=str(job_id),
        local_job_id=job_id,
        requested_targets=(PublicExamConverterTarget.EXAMNET_PDF,),
        status=PublicExamConverterJobStatus.QUEUED,
        source_filename="exam.dxe",
        submitted_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        correlation_id=None,
        source_dxe=PublicExamConverterUpload(
            filename="exam.dxe",
            content_type="application/octet-stream",
            file_bytes=b"dxe",
        ),
    )


async def _admit_public_job(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    job: PublicExamConverterSubmittedJob,
    now: datetime,
) -> PublicExamConverterSubmittedJob | None:
    async with session_factory() as session, session.begin():
        return await PostgreSQLPublicExamConverterJobRepository(session).create_if_capacity(
            job=job,
            now=now,
            concurrency_limit=1,
        )


async def test_public_capacity_check_and_enqueue_are_one_transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    first, second = await asyncio.gather(
        _admit_public_job(
            session_factory=session_factory,
            job=_public_candidate(now=now),
            now=now,
        ),
        _admit_public_job(
            session_factory=session_factory,
            job=_public_candidate(now=now),
            now=now,
        ),
    )

    assert sum(job is not None for job in (first, second)) == 1


async def test_public_job_claim_and_heartbeat_keep_one_worker_owner(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC) + timedelta(hours=2)
    admitted = await _admit_public_job(
        session_factory=session_factory,
        job=_public_candidate(now=now),
        now=now,
    )
    assert admitted is not None
    lease_ttl = timedelta(minutes=15)

    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        claimed = await repository.claim_next(
            worker_id="worker-1",
            now=now,
            lease_ttl=lease_ttl,
        )
    assert claimed is not None
    assert claimed.local_job_id == admitted.local_job_id

    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        assert await repository.heartbeat(
            local_job_id=claimed.local_job_id,
            worker_id="worker-1",
            now=now + timedelta(minutes=1),
            lease_ttl=lease_ttl,
        )
        assert not await repository.heartbeat(
            local_job_id=claimed.local_job_id,
            worker_id="worker-2",
            now=now + timedelta(minutes=1),
            lease_ttl=lease_ttl,
        )

    after_expiry = now + timedelta(minutes=20)
    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        reaped = await repository.claim_next_expired(
            worker_id="worker-2",
            now=after_expiry,
            lease_ttl=lease_ttl,
        )
    assert reaped is not None
    assert reaped.local_job_id == claimed.local_job_id

    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        with pytest.raises(DomainError) as raised:
            await repository.update(
                job=replace(
                    claimed,
                    status=PublicExamConverterJobStatus.SUCCEEDED,
                    locked_by=None,
                    locked_until=None,
                ),
                expected_worker_id="worker-1",
            )
    assert raised.value.code is ErrorCode.CONFLICT


async def test_public_job_update_rejects_missing_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    missing = _public_candidate(now=datetime.now(UTC))

    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        with pytest.raises(DomainError) as raised:
            await repository.update(job=missing)

    assert raised.value.code is ErrorCode.NOT_FOUND


async def test_public_job_expiration_deletes_persisted_input(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2001, 1, 1, tzinfo=UTC)
    expired = replace(
        _public_candidate(now=now),
        expires_at=now - timedelta(seconds=1),
    )
    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        admitted = await repository.create_if_capacity(
            job=expired,
            now=datetime(1999, 1, 1, tzinfo=UTC),
            concurrency_limit=1_000_000,
        )
    assert admitted is not None

    async with session_factory() as session, session.begin():
        repository = PostgreSQLPublicExamConverterJobRepository(session)
        deleted_id = await repository.delete_next_expired(now=now)
    assert deleted_id == expired.local_job_id

    async with session_factory() as session:
        assert await session.get(PublicExamConverterJobModel, expired.local_job_id) is None


async def _claim_expired_enrichment(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    now: datetime,
) -> UUID | None:
    async with session_factory() as session, session.begin():
        claimed = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).claim_next_expired(
            worker_id=f"reaper-{uuid4()}",
            now=now,
            lease_ttl=timedelta(minutes=15),
        )
        return claimed.id if claimed is not None else None


async def test_expired_enrichment_job_has_one_reaper_and_renewable_lease(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id = await _create_owner(session_factory)
    conversion_job, _ = await _acquire(
        session_factory=session_factory,
        candidate=_candidate(owner_id=owner_id, submission_key=f"enrichment-{uuid4()}"),
    )
    now = datetime.now(UTC)
    enrichment = enqueue_enrichment_job(
        job_id=uuid4(),
        conversion_job_id=conversion_job.id,
        owner_user_id=owner_id,
        input_filename="exam.dxe",
        source_dxe=b"dxe",
        now=now,
    )
    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        await repository.create(job=enrichment)
        claimed = await repository.claim_next(
            worker_id="worker-1",
            now=now,
            lease_ttl=timedelta(seconds=1),
        )
    assert claimed is not None

    after_expiry = now + timedelta(seconds=2)
    first, second = await asyncio.gather(
        _claim_expired_enrichment(session_factory=session_factory, now=after_expiry),
        _claim_expired_enrichment(session_factory=session_factory, now=after_expiry),
    )
    assert sum(job_id is not None for job_id in (first, second)) == 1

    reaper_job_id = first or second
    assert reaper_job_id == enrichment.id

    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        with pytest.raises(DomainError) as raised:
            await repository.update(
                job=finish_enrichment_job(
                    job=claimed,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=after_expiry,
                ),
                expected_worker_id="worker-1",
            )
    assert raised.value.code is ErrorCode.CONFLICT
