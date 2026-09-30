"""In-memory fakes and a harness for the conversion submit-handler routing tests.

Purpose:
    Give the enrichment-routing tests protocol fakes for the conversion-hub and
    enrichment job repositories, a recording producer and artifact store, DXE
    upload builders, and one harness wiring them into
    `CreateExamConverterConversionJobsHandler`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionStoredArtifact,
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

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


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

    async def acquire_by_owner_and_submission_key(
        self, *, job: ConversionHubJob
    ) -> tuple[ConversionHubJob, bool]:
        existing = next(
            (
                stored
                for stored in self.jobs.values()
                if stored.owner_user_id == job.owner_user_id
                and stored.submission_idempotency_key == job.submission_idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.status is not ConversionHubJobStatus.FAILED:
                return existing, False
            self.jobs[existing.id] = existing.model_copy(
                update={"submission_idempotency_key": None}
            )
        self.jobs[job.id] = job
        return job, True

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class InMemoryEnrichmentJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ExamAnswerKeyEnrichmentJob] = {}

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        self.jobs[job.id] = job
        return job

    async def update(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        expected_worker_id: str | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        current = self.jobs.get(job.id)
        if (
            expected_worker_id is not None
            and current is not None
            and current.locked_by != expected_worker_id
        ):
            raise AssertionError("worker lease is no longer owned")
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
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        del worker_id, now, lease_ttl
        return None

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        del job_id, worker_id, now, lease_ttl
        return False


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

    def delete_artifact(self, *, job_id: UUID) -> None:
        self.stored.pop(job_id, None)


def make_actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        email_verified=True,
        created_at=NOW,
        updated_at=NOW,
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


_PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def make_upload(
    *, keyed: bool, include_open_ended: bool = False, include_asset_item: bool = False
) -> ConversionHubUpload:
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
    if include_asset_item:
        questions.append(
            {
                "id": 3,
                "title": "Gap with image",
                "about": "",
                "bodyHTML": (
                    '<p><img data-image-id="0" class="fr-fic fr-dib"/></p>'
                    "<p>Fill in the missing word.</p>"
                ),
                "images": [_PNG_1X1_BASE64],
                "maxScore": 2,
                "type": 3,
                "blanks": [{"guid": "gap-1", "validations": []}],
            }
        )
    payload = {"exams": [{"questions": questions}]}
    return ConversionHubUpload(
        filename="exam.dxe",
        content_type="application/octet-stream",
        file_bytes=json.dumps(payload).encode("utf-8"),
    )


class RoutingHarness:
    def __init__(self, *, enrichment_enabled: bool) -> None:
        self.jobs = InMemoryConversionHubJobRepository()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.producer = RecordingProducer()
        self.artifacts = RecordingArtifactStore()
        self.handler = CreateExamConverterConversionJobsHandler(
            jobs=self.jobs,
            producer=self.producer,
            artifacts=self.artifacts,
            enrichment_jobs=self.enrichment_jobs,
            enrichment_enabled=enrichment_enabled,
            uow=FakeUow(),
            clock=FixedClock(),
            id_generator=UUIDGenerator(),
            submission_lookup=self.jobs,
        )
