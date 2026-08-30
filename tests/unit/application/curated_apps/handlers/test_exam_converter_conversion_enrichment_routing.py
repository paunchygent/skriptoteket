"""Routing tests for the in-process conversion submit handler.

Purpose:
    Prove readiness parity at the submit boundary: source-keyed and
    overlay-keyed uploads keep the synchronous ST-SKRIPT-39-01 path, a
    disabled answer-key lane changes nothing, and only overlay-free unkeyed
    exams enqueue one enrichment worker job without blocking the request.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_converter_conversions`
      with in-memory protocol fakes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionStoredArtifact,
    ExamConverterConversionLane,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_converter_conversions import (
    CreateExamConverterConversionJobsHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    SourceBoundCorrectionIntent,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from tests.fixtures.application_fixtures import FakeUow

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return _NOW


class UUIDGenerator:
    def new_uuid(self) -> UUID:
        return uuid4()


class InMemoryConversionHubJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ConversionHubJob] = {}

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.jobs.get(job_id)

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        return None

    async def get_by_owner_and_submission_key(
        self, *, owner_user_id: UUID, submission_idempotency_key: str
    ) -> ConversionHubJob | None:
        return next(
            (
                job
                for job in self.jobs.values()
                if job.owner_user_id == owner_user_id
                and job.submission_idempotency_key == submission_idempotency_key
            ),
            None,
        )

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class InMemoryEnrichmentJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ExamAnswerKeyEnrichmentJob] = {}

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        self.jobs[job.id] = job
        return job

    async def update(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        return self.jobs.get(job_id)

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        return None

    async def claim_next_expired(
        self,
        *,
        now: datetime,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        return None


class RecordingProducer:
    """Producer double that converts synchronously and records its calls."""

    def __init__(self) -> None:
        self.calls = 0

    async def convert(
        self,
        *,
        job_id: UUID,
        upload: ConversionHubUpload,
        overlay_bytes: bytes | None,
        proposal_overlay_bytes: bytes | None = None,
        proposal_provider_profile_id: str | None = None,
        proposal_model: str | None = None,
        teacher_answer_key_item_ids: frozenset[str] = frozenset(),
        correction_intents: tuple[SourceBoundCorrectionIntent, ...] = (),
        enrichment_failure_code: str | None = None,
        retry_identity: str | None = None,
        correlation_id: str | None,
        overlay_key_provenance: DigiExamAnswerKeyProvenance = (
            DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
        ),
    ) -> ExamConversionStoredArtifact:
        del job_id, proposal_overlay_bytes, proposal_provider_profile_id, proposal_model
        del teacher_answer_key_item_ids, correction_intents, enrichment_failure_code, retry_identity
        self.calls += 1
        return ExamConversionStoredArtifact(
            filename="exam-examnet-bundle.zip",
            content_type="application/zip",
            content=b"bundle",
            source_filename=upload.filename,
            source_content=upload.file_bytes,
        )


class RecordingArtifactStore:
    def __init__(self) -> None:
        self.stored: dict[UUID, ExamConversionStoredArtifact] = {}

    def store_artifact(self, *, job_id: UUID, artifact: ExamConversionStoredArtifact) -> None:
        self.stored[job_id] = artifact

    def read_artifact(self, *, job_id: UUID) -> ExamConversionStoredArtifact:
        return self.stored[job_id]

    def read_named_artifact(self, *, job_id: UUID, artifact_key: str):
        return next(
            artifact
            for artifact in self.stored[job_id].named_artifacts
            if artifact.artifact_key == artifact_key
        )


def _actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        email_verified=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _question(*, keyed: bool) -> dict[str, JsonValue]:
    return {
        "id": 1,
        "title": "Single choice",
        "about": "",
        "bodyHTML": "<p>Choose the Greek letter.</p>",
        "images": [],
        "maxScore": 2,
        "type": 1,
        "alternatives": [
            {"id": 1, "title": "Alpha", "about": "", "right": False},
            {"id": 2, "title": "Beta", "about": "", "right": keyed},
        ],
    }


def _upload(*, keyed: bool, include_open_ended: bool = False) -> ConversionHubUpload:
    questions = [_question(keyed=keyed)]
    if include_open_ended:
        questions.append(
            {
                "id": 2,
                "title": "Essay",
                "about": "",
                "bodyHTML": "<p>Explain.</p>",
                "images": [],
                "maxScore": 4,
                "type": 0,
            }
        )
    payload = {"exams": [{"questions": questions}]}
    return ConversionHubUpload(
        filename="exam.dxe",
        content_type="application/octet-stream",
        file_bytes=json.dumps(payload).encode("utf-8"),
    )


class _Harness:
    def __init__(self, *, enrichment_enabled: bool) -> None:
        self.jobs = InMemoryConversionHubJobRepository()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.producer = RecordingProducer()
        self.artifacts = RecordingArtifactStore()
        self.handler = CreateExamConverterConversionJobsHandler(
            jobs=self.jobs,
            lane=ExamConverterConversionLane(value="in_process"),
            producer=self.producer,
            artifacts=self.artifacts,
            enrichment_jobs=self.enrichment_jobs,
            enrichment_enabled=enrichment_enabled,
            uow=FakeUow(),
            clock=FixedClock(),
            id_generator=UUIDGenerator(),
            submission_lookup=self.jobs,
        )


async def test_unkeyed_upload_enqueues_one_enrichment_job_without_converting() -> None:
    harness = _Harness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=_actor(),
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUBMITTED
    assert harness.producer.calls == 0
    assert len(harness.enrichment_jobs.jobs) == 1
    enrichment_job = next(iter(harness.enrichment_jobs.jobs.values()))
    assert enrichment_job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED
    assert enrichment_job.conversion_job_id == result.job_id
    assert enrichment_job.source_dxe == _upload(keyed=False).file_bytes


async def test_repeated_native_submission_returns_the_existing_job() -> None:
    harness = _Harness(enrichment_enabled=True)
    actor = _actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="same-native-submit",
    )
    second = await harness.handler.handle(
        actor=actor,
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-response-retry",
        idempotency_key="same-native-submit",
    )

    assert second.job_id == first.job_id
    assert second.idempotent_replay is True
    assert len(harness.jobs.jobs) == 1
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_advisory_retry_identity_creates_a_distinct_enrichment_attempt() -> None:
    harness = _Harness(enrichment_enabled=True)
    actor = _actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="native-submit-retry-1",
        advisory_retry_attempt=1,
    )
    second = await harness.handler.handle(
        actor=actor,
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-second",
        idempotency_key="native-submit-retry-2",
        advisory_retry_attempt=2,
    )

    assert second.job_id != first.job_id
    retry_identities = {job.retry_identity for job in harness.enrichment_jobs.jobs.values()}
    assert retry_identities == {
        "native-submit-retry-1:advisory:1",
        "native-submit-retry-2:advisory:2",
    }


async def test_mixed_manual_marking_upload_enqueues_supported_unkeyed_items() -> None:
    harness = _Harness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=_actor(),
        upload=_upload(keyed=False, include_open_ended=True),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUBMITTED
    assert harness.producer.calls == 0
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_source_keyed_upload_keeps_the_synchronous_path() -> None:
    harness = _Harness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=_actor(),
        upload=_upload(keyed=True),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}


async def test_overlay_upload_keeps_the_synchronous_path() -> None:
    harness = _Harness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=_actor(),
        upload=_upload(keyed=False),
        overlay_bytes=b"{}",
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}


async def test_disabled_answer_key_lane_changes_nothing_for_unkeyed_uploads() -> None:
    harness = _Harness(enrichment_enabled=False)

    result = await harness.handler.handle(
        actor=_actor(),
        upload=_upload(keyed=False),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}
