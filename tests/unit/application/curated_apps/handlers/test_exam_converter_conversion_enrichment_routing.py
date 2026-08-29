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


class RecordingProducer:
    """Producer double that converts synchronously and records its calls."""

    def __init__(self) -> None:
        self.calls = 0

    async def convert(
        self,
        *,
        upload: ConversionHubUpload,
        overlay_bytes: bytes | None,
        correlation_id: str | None,
        overlay_key_provenance: DigiExamAnswerKeyProvenance = (
            DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
        ),
    ) -> ExamConversionStoredArtifact:
        self.calls += 1
        return ExamConversionStoredArtifact(
            filename="exam-examnet-bundle.zip",
            content_type="application/zip",
            content=b"bundle",
        )


class RecordingArtifactStore:
    def __init__(self) -> None:
        self.stored: dict[UUID, ExamConversionStoredArtifact] = {}

    def store_artifact(self, *, job_id: UUID, artifact: ExamConversionStoredArtifact) -> None:
        self.stored[job_id] = artifact

    def read_artifact(self, *, job_id: UUID) -> ExamConversionStoredArtifact:
        return self.stored[job_id]


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


def _upload(*, keyed: bool) -> ConversionHubUpload:
    payload = {"exams": [{"questions": [_question(keyed=keyed)]}]}
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
