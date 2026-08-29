"""Worker-job lifecycle tests for machine answer-key enrichment.

Purpose:
    Prove the enrichment processor with a stubbed provider: lease reserved
    before the call and reconciled from reported usage, machine-proposed
    overlay persisted, conversion completed; the typed lease refusal makes
    zero provider calls; provider failures never refund the lease.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against in-memory protocol fakes and an injected clock.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    enqueue_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    AnswerKeyTokenLeaseState,
    charged_lease_tokens,
    lease_utc_day,
    refuse_lease,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.infrastructure.llm.openai.answer_key_profiles import (
    LunaOnlyAnswerKeyProviderSelector,
)
from tests.fixtures.application_fixtures import FakeUow

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


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
        for job in self.jobs.values():
            if job.upstream_job_id == upstream_job_id:
                return job
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
        for job in self.jobs.values():
            if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED:
                claimed = job.model_copy(
                    update={
                        "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
                        "attempts": job.attempts + 1,
                        "locked_by": worker_id,
                        "locked_until": now + lease_ttl,
                        "updated_at": now,
                    }
                )
                self.jobs[job.id] = claimed
                return claimed
        return None

    async def claim_next_expired(
        self,
        *,
        now: datetime,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if (
                job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
                and job.locked_until is not None
                and job.locked_until < now
            ):
                return job
        return None


class InMemoryLeaseRepository:
    """In-memory mirror of the Postgres lease semantics for lifecycle tests."""

    def __init__(self, *, daily_token_limit: int) -> None:
        self._daily_token_limit = daily_token_limit
        self.leases: dict[UUID, AnswerKeyTokenLease] = {}

    async def reserve(
        self,
        *,
        now: datetime,
        requested_tokens: int,
        job_id: UUID,
        item_id: str,
        provider_profile_id: str,
    ) -> AnswerKeyTokenLease:
        utc_day = lease_utc_day(now)
        usage = await self.day_usage(utc_day=utc_day)
        if usage.available_tokens < requested_tokens:
            raise refuse_lease(usage=usage, requested_tokens=requested_tokens)
        lease = AnswerKeyTokenLease(
            lease_id=uuid4(),
            utc_day=utc_day,
            reserved_tokens=requested_tokens,
            state=AnswerKeyTokenLeaseState.RESERVED,
        )
        self.leases[lease.lease_id] = lease
        return lease

    async def reconcile(self, *, lease_id: UUID, actual_tokens: int, now: datetime) -> None:
        lease = self.leases[lease_id]
        self.leases[lease_id] = AnswerKeyTokenLease(
            lease_id=lease.lease_id,
            utc_day=lease.utc_day,
            reserved_tokens=lease.reserved_tokens,
            state=AnswerKeyTokenLeaseState.RECONCILED,
            actual_tokens=actual_tokens,
        )

    async def day_usage(self, *, utc_day: date) -> AnswerKeyTokenLeaseDayUsage:
        charged = sum(
            charged_lease_tokens(
                reserved_tokens=lease.reserved_tokens,
                actual_tokens=lease.actual_tokens,
            )
            for lease in self.leases.values()
            if lease.utc_day == utc_day
        )
        return AnswerKeyTokenLeaseDayUsage(
            utc_day=utc_day,
            daily_token_limit=self._daily_token_limit,
            charged_tokens=charged,
        )


class InMemoryProposedOverlayRepository:
    def __init__(self) -> None:
        self.records: list[ExamAnswerKeyProposedOverlay] = []

    async def create(
        self,
        *,
        proposed_overlay: ExamAnswerKeyProposedOverlay,
    ) -> ExamAnswerKeyProposedOverlay:
        self.records.append(proposed_overlay)
        return proposed_overlay

    async def get_by_conversion_job_id(
        self,
        *,
        conversion_job_id: UUID,
    ) -> ExamAnswerKeyProposedOverlay | None:
        for record in self.records:
            if record.conversion_job_id == conversion_job_id:
                return record
        return None


class StubProvider:
    def __init__(self, *, content: dict[str, JsonValue], usage: StructuredLLMUsage) -> None:
        self._content = content
        self._usage = usage
        self.call_count = 0

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        self.call_count += 1
        return StructuredLLMResponse(
            content=self._content,
            finish_reason="completed",
            usage=self._usage,
        )


class FailingProvider:
    def __init__(self) -> None:
        self.call_count = 0

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        self.call_count += 1
        raise StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
            message="Structured provider request timed out.",
            provider_id=profile.provider_id,
        )


class RecordingProducer:
    def __init__(self) -> None:
        self.overlay_bytes: bytes | None = None
        self.overlay_key_provenance: DigiExamAnswerKeyProvenance | None = None

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
        self.overlay_bytes = overlay_bytes
        self.overlay_key_provenance = overlay_key_provenance
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


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
    )


def _unkeyed_dxe_bytes(*, include_open_ended: bool = False) -> bytes:
    questions: list[dict[str, JsonValue]] = [
        {
            "id": 1,
            "title": "Single without key",
            "about": "",
            "bodyHTML": "<p>Choose the Greek letter.</p>",
            "images": [],
            "maxScore": 2,
            "type": 1,
            "alternatives": [
                {"id": 1, "title": "Alpha", "about": "", "right": False},
                {"id": 2, "title": "Beta", "about": "", "right": False},
            ],
        }
    ]
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
    return json.dumps({"exams": [{"questions": questions}]}).encode("utf-8")


class _Harness:
    def __init__(
        self,
        *,
        provider: StubProvider | FailingProvider,
        daily_token_limit: int = 1_000_000,
    ) -> None:
        self.conversion_jobs = InMemoryConversionHubJobRepository()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.leases = InMemoryLeaseRepository(daily_token_limit=daily_token_limit)
        self.proposed_overlays = InMemoryProposedOverlayRepository()
        self.provider = provider
        self.producer = RecordingProducer()
        self.artifacts = RecordingArtifactStore()
        self.handler = ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=self.enrichment_jobs,
            conversion_jobs=self.conversion_jobs,
            leases=self.leases,
            proposed_overlays=self.proposed_overlays,
            provider=provider,
            provider_selector=LunaOnlyAnswerKeyProviderSelector(profile=_profile()),
            producer=self.producer,
            artifacts=self.artifacts,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            id_generator=UUIDGenerator(),
        )

    async def seed_claimed_job(
        self,
        *,
        source_dxe: bytes | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        conversion_job = ConversionHubJob(
            id=uuid4(),
            owner_user_id=uuid4(),
            input_filename="exam.dxe",
            source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
            output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
            status=ConversionHubJobStatus.SUBMITTED,
            created_at=_NOW,
            updated_at=_NOW,
        )
        await self.conversion_jobs.create(job=conversion_job)
        await self.enrichment_jobs.create(
            job=enqueue_enrichment_job(
                job_id=uuid4(),
                conversion_job_id=conversion_job.id,
                owner_user_id=conversion_job.owner_user_id,
                input_filename="exam.dxe",
                source_dxe=source_dxe or _unkeyed_dxe_bytes(),
                now=_NOW,
            )
        )
        claimed = await self.enrichment_jobs.claim_next(
            worker_id="worker-1",
            now=_NOW,
            lease_ttl=timedelta(seconds=900),
        )
        assert claimed is not None
        return claimed


async def test_successful_job_reserves_reconciles_and_completes_conversion() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        )
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 190
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert conversion_job.upstream_job_id == f"local-exam:{job.conversion_job_id}"
    assert harness.producer.overlay_key_provenance is (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    assert harness.producer.overlay_bytes is not None
    assert job.conversion_job_id in harness.artifacts.stored
    proposal = harness.proposed_overlays.records[0]
    assert proposal.conversion_job_id == job.conversion_job_id
    assert proposal.provider_profile_id == "openai-gpt-5.6-luna"
    assert proposal.model == "gpt-5.6-luna"
    overlay_items = proposal.overlay_json["items"]
    assert isinstance(overlay_items, list)
    assert len(overlay_items) == 1


async def test_mixed_exam_enriches_only_supported_item_and_completes_conversion() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        )
    )
    job = await harness.seed_claimed_job(source_dxe=_unkeyed_dxe_bytes(include_open_ended=True))

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1
    assert len(harness.leases.leases) == 1
    proposal = harness.proposed_overlays.records[0]
    overlay_items = proposal.overlay_json["items"]
    assert isinstance(overlay_items, list)
    assert len(overlay_items) == 1
    overlay_item = overlay_items[0]
    assert isinstance(overlay_item, dict)
    assert overlay_item["item_id"] == "item-001"
    assert harness.producer.overlay_key_provenance is (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED


async def test_lease_refusal_fails_closed_with_zero_provider_calls() -> None:
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _Harness(provider=provider, daily_token_limit=10)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "daily_token_lease_exhausted"
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.FAILED
    assert conversion_job.error_message is not None
    assert "2026-08-30 00:00" in conversion_job.error_message
    assert harness.proposed_overlays.records == []


async def test_provider_failure_never_refunds_the_reserved_lease() -> None:
    harness = _Harness(provider=FailingProvider())
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_timeout"
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RESERVED
    assert leases[0].actual_tokens is None
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == leases[0].reserved_tokens
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.FAILED


async def test_invalid_model_output_fails_without_a_proposal() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [9]},
            usage=StructuredLLMUsage(total_tokens=50),
        )
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
    leases = list(harness.leases.leases.values())
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 50
    assert harness.proposed_overlays.records == []
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.FAILED


async def test_expired_running_job_fail_closes_both_jobs_without_calls_or_refund() -> None:
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _Harness(provider=provider)
    job = await harness.seed_claimed_job()
    await harness.leases.reserve(
        now=_NOW,
        requested_tokens=300,
        job_id=job.id,
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )

    still_leased = await harness.handler.fail_next_expired(now=_NOW)
    assert still_leased is None

    after_expiry = _NOW + timedelta(seconds=1800)
    failed = await harness.handler.fail_next_expired(now=after_expiry)

    assert failed is not None
    assert failed.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert failed.last_error == "enrichment_worker_lease_expired"
    assert failed.locked_by is None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.FAILED
    assert conversion_job.error_message is not None
    assert provider.call_count == 0
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RESERVED
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == 300
    assert await harness.handler.fail_next_expired(now=after_expiry) is None
