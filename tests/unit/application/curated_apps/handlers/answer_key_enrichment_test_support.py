"""In-memory fakes and builders for the machine answer-key enrichment tests.

Purpose:
    Give the enrichment lifecycle tests protocol fakes for the conversion-hub,
    enrichment, lease, and proposed-overlay repositories, scripted structured
    providers, a recording producer and artifact store, provider-route
    builders, and the DOCX import processor wiring the enrichment dispatcher
    requires.

Relationships:
    - Shared by `test_exam_answer_key_enrichment_jobs` and the workspace
      enrichment, DOCX job, and repository tests that reuse its fakes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJob
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMEndpointKind,
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
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)

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

    async def get_conversion_view(self, *, job_id: UUID) -> ExamWorkspaceConversionJobView | None:
        job = self.jobs.get(job_id)
        return (
            ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
            if job
            else None
        )

    async def get_by_id_for_update(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        return self.jobs.get(job_id)

    async def get_by_workspace_revision(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if (
                job.owner_user_id == owner_user_id
                and job.workspace_lineage_id == workspace_lineage_id
                and job.workspace_document_revision == workspace_document_revision
            ):
                return job
        return None

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED and (
                source_kind is None or job.source_kind is source_kind
            ):
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
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if (
                job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
                and job.locked_until is not None
                and job.locked_until < now
                and (source_kind is None or job.source_kind is source_kind)
            ):
                claimed = job.model_copy(
                    update={
                        "locked_by": worker_id,
                        "locked_until": now + lease_ttl,
                        "updated_at": now,
                    }
                )
                self.jobs[job.id] = claimed
                return claimed
        return None

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.locked_by != worker_id:
            return False
        self.jobs[job_id] = job.model_copy(
            update={"locked_until": now + lease_ttl, "updated_at": now}
        )
        return True


class InMemoryLeaseRepository:
    """In-memory mirror of the Postgres lease semantics for lifecycle tests."""

    def __init__(self, *, daily_token_limit: int) -> None:
        self._daily_token_limit = daily_token_limit
        self.leases: dict[UUID, AnswerKeyTokenLease] = {}
        self.profile_by_lease: dict[UUID, str] = {}

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
        self.profile_by_lease[lease.lease_id] = provider_profile_id
        return lease

    def leases_for_profile(self, provider_profile_id: str) -> list[AnswerKeyTokenLease]:
        return [
            lease
            for lease_id, lease in self.leases.items()
            if self.profile_by_lease[lease_id] == provider_profile_id
        ]

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

    async def get_by_enrichment_job_id(
        self,
        *,
        enrichment_job_id: UUID,
    ) -> ExamAnswerKeyProposedOverlay | None:
        for record in self.records:
            if record.enrichment_job_id == enrichment_job_id:
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


def _failover_profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openrouter-glm-5.3-flash",
        model="z-ai/glm-5.3-flash",
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


def _route() -> AnswerKeyProviderRoute:
    return AnswerKeyProviderRoute(primary=_profile(), failover=_failover_profile())


def docx_job_handler(
    *,
    enrichment_jobs: InMemoryEnrichmentJobRepository,
    proposed_overlays: InMemoryProposedOverlayRepository,
    leases: InMemoryLeaseRepository,
    provider: AnswerKeyStructuredProviderProtocol,
    vault_files: InMemoryVaultFileRepository,
    vault_storage: InMemoryVaultStorage,
    codec: ExamWorkspaceContainerCodecProtocol,
) -> ProcessExamWorkspaceDocxJobHandler:
    """Wire the DOCX import processor the enrichment dispatcher requires."""

    uow = FakeUow()
    clock = FixedClock(_NOW)
    id_generator = UUIDGenerator()
    return ProcessExamWorkspaceDocxJobHandler(
        jobs=enrichment_jobs,
        chunker=PythonDocxExamChunker(),
        converter=DocxAIConverter(
            provider=provider,
            profile=_route().primary,
            leases=leases,
            uow=uow,
            clock=clock,
            enabled=True,
        ),
        codec=codec,
        store=ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=InMemoryVaultUsageRepository(
                usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=_NOW)
            ),
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000,
                VAULT_MAX_TOTAL_BYTES=50_000_000,
            ),
            proposal_carry_forward=CarryExamWorkspaceProposals(
                enrichment_jobs=enrichment_jobs,
                proposed_overlays=proposed_overlays,
                clock=clock,
                id_generator=id_generator,
            ),
        ),
        users=UserRepositoryStub(),
        uow=uow,
        clock=clock,
        id_generator=id_generator,
    )
