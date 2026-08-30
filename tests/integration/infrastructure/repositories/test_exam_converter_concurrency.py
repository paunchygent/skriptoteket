"""Concurrent PostgreSQL coverage for native Exam Converter ownership seams."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
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
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_converter_correction_sessions import (
    PostgreSQLExamConverterCorrectionSessionRepository,
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
