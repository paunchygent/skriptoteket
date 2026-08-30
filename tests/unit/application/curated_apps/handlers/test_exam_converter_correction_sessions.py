"""Tests for Exam Converter correction-session application handlers.

Purpose:
  Prove PR-0334 read, replacement, revert, owner-scope, and conflict behavior before
  frontend or replay orchestration consumes the API contract.

Relationships:
  - Exercises `application.curated_apps.handlers.exam_converter_correction_sessions`.
  - Uses PR-0333 aggregate semantics through fake repository protocols.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentWrite,
    ReplaceExamConverterCorrectionIntentsRequest,
    RevertExamConverterCorrectionIntentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_correction_sessions import (
    GetExamConverterCorrectionSessionHandler,
    ReplaceExamConverterCorrectionIntentsHandler,
    RevertExamConverterCorrectionIntentHandler,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user


class InMemoryConversionHubJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ConversionHubJob] = {}

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.jobs.get(job_id)

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        for job in self.jobs.values():
            if job.upstream_job_id == upstream_job_id:
                return job
        return None

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class InMemoryCorrectionSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[tuple[UUID, UUID], ExamConverterCorrectionSession] = {}
        self.locked_jobs: list[tuple[UUID, UUID]] = []
        self.save_calls = 0

    async def lock_owned_job(self, *, owner_user_id: UUID, conversion_hub_job_id: UUID) -> None:
        self.locked_jobs.append((owner_user_id, conversion_hub_job_id))

    async def get_by_owner_and_job(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ExamConverterCorrectionSession | None:
        return self.sessions.get((owner_user_id, conversion_hub_job_id))

    async def save(
        self,
        *,
        session: ExamConverterCorrectionSession,
        expected_session_version: int,
    ) -> ExamConverterCorrectionSession:
        self.save_calls += 1
        current = self.sessions.get((session.owner_user_id, session.conversion_hub_job_id))
        current_version = current.session_version if current is not None else 0
        if current_version != expected_session_version:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Exam Converter correction session version conflict",
                details={"current_session_version": current_version},
            )
        self.sessions[(session.owner_user_id, session.conversion_hub_job_id)] = session
        return session


class SequenceIdGenerator:
    def __init__(self, ids: list[UUID]) -> None:
        self._ids = ids

    def new_uuid(self) -> UUID:
        return self._ids.pop(0)


def _binding() -> ExamConverterCorrectionSourceBinding:
    return ExamConverterCorrectionSourceBinding(
        source_authoring_schema_version="exam_authoring_ir_v1",
        source_bundle_id="bundle-001",
        source_file_sha256="sha256:source-file",
        source_state_sha256="sha256:source-state",
        source_state_signature="signed-source-state",
    )


def _intent(
    kind: str = "point_correction",
    *,
    item_id: str = "item-001",
    sequence: int = 1,
) -> ExamConverterCorrectionIntentWrite:
    return ExamConverterCorrectionIntentWrite(
        entry_id=f"entry-{kind}-{item_id}",
        source_binding=_binding(),
        item_id=item_id,
        sequence=sequence,
        item_type="multiple_choice",
        source_item_fingerprint=f"sha256:{item_id}",
        kind=kind,
        target=ExamConverterCorrectionTarget(),
        payload={"kind": kind, "max_score": 2},
    )


def _job(*, owner_user_id: UUID, job_id: UUID) -> ConversionHubJob:
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename="exam.dxe",
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.PDF,
        status=ConversionHubJobStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_batch_and_read_return_current_active_set() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    sessions = InMemoryCorrectionSessionRepository()
    replace = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4(), uuid4()]),
    )
    read = GetExamConverterCorrectionSessionHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
    )

    result = await replace.handle(
        actor=actor,
        job_id=job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[_intent(), _intent(item_id="item-002", sequence=2)],
        ),
    )
    readback = await read.handle(actor=actor, job_id=job_id)

    assert result.session_version == 1
    assert sessions.locked_jobs == [(actor.id, job_id)]
    assert sessions.save_calls == 1
    assert [intent.item_id for intent in readback.active_intents] == ["item-001", "item-002"]
    assert readback.source_binding == _binding()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_one_intent_list_works() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    handler = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=InMemoryCorrectionSessionRepository(),
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )

    result = await handler.handle(
        actor=actor,
        job_id=job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[_intent()],
        ),
    )

    assert result.session_version == 1
    assert len(result.active_intents) == 1


@pytest.mark.unit
def test_replace_request_rejects_empty_intents() -> None:
    with pytest.raises(ValidationError):
        ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[],
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_expected_version_is_conflict() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    sessions = InMemoryCorrectionSessionRepository()
    handler = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4(), uuid4()]),
    )
    await handler.handle(
        actor=actor,
        job_id=job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[_intent()],
        ),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            job_id=job_id,
            request=ReplaceExamConverterCorrectionIntentsRequest(
                expected_session_version=0,
                intents=[_intent()],
            ),
        )

    assert exc.value.code is ErrorCode.CONFLICT
    assert exc.value.details["current_session_version"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_batch_fails_without_repository_save() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    sessions = InMemoryCorrectionSessionRepository()
    handler = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4(), uuid4()]),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            job_id=job_id,
            request=ReplaceExamConverterCorrectionIntentsRequest(
                expected_session_version=0,
                intents=[_intent(), _intent()],
            ),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert sessions.save_calls == 0
    assert sessions.sessions == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_owner_scoping_rejects_other_user_job() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=uuid4(), job_id=job_id)
    handler = GetExamConverterCorrectionSessionHandler(
        jobs=jobs,
        sessions=InMemoryCorrectionSessionRepository(),
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=actor, job_id=job_id)

    assert exc.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsupported_matching_kind_is_validation_error() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    handler = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=InMemoryCorrectionSessionRepository(),
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            job_id=job_id,
            request=ReplaceExamConverterCorrectionIntentsRequest(
                expected_session_version=0,
                intents=[_intent("manual_matching_answer_key")],
            ),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revert_deletes_active_intent() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    sessions = InMemoryCorrectionSessionRepository()
    replace = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )
    revert = RevertExamConverterCorrectionIntentHandler(
        jobs=jobs,
        sessions=sessions,
        uow=FakeUow(),
    )
    saved = await replace.handle(
        actor=actor,
        job_id=job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[_intent()],
        ),
    )

    result = await revert.handle(
        actor=actor,
        job_id=job_id,
        request=RevertExamConverterCorrectionIntentRequest(
            expected_session_version=1,
            target_key=saved.active_intents[0].target_key,
        ),
    )

    assert result.session_version == 2
    assert result.active_intents == []
