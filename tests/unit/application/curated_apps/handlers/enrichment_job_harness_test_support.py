"""Scripted provider, recording producer, and harness for the enrichment lifecycle tests.

Purpose:
    Give the DXE enrichment lifecycle tests a provider that yields one scripted
    outcome per call, a producer recording the overlay it was handed, and one
    harness wiring the in-memory fakes into `ProcessExamAnswerKeyEnrichmentJobHandler`.

Relationships:
    - Builds on the shared fakes in `answer_key_enrichment_test_support`.
"""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    enqueue_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    SourceBoundCorrectionIntent,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    _NOW,
    FixedClock,
    InMemoryConversionHubJobRepository,
    InMemoryEnrichmentJobRepository,
    InMemoryLeaseRepository,
    InMemoryProposedOverlayRepository,
    RecordingArtifactStore,
    StubProvider,
    UUIDGenerator,
    _route,
    docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
)


class SequenceProvider:
    """Yield one scripted outcome per call and record the profile order."""

    def __init__(
        self,
        *,
        outcomes: tuple[StructuredLLMResponse | StructuredLLMProviderError, ...],
    ) -> None:
        self._outcomes = outcomes
        self.profiles: list[StructuredLLMProviderProfile] = []

    @property
    def call_count(self) -> int:
        return len(self.profiles)

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        outcome = self._outcomes[len(self.profiles)]
        self.profiles.append(profile)
        if isinstance(outcome, StructuredLLMProviderError):
            raise outcome
        return outcome


class RecordingProducer:
    def __init__(self) -> None:
        self.overlay_bytes: bytes | None = None
        self.overlay_key_provenance: DigiExamAnswerKeyProvenance | None = None

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
        self.overlay_bytes = overlay_bytes
        self.overlay_key_provenance = overlay_key_provenance
        return ExamConversionStoredArtifact(
            filename="exam-examnet-bundle.zip",
            content_type="application/zip",
            content=b"bundle",
            source_filename=upload.filename,
            source_content=upload.file_bytes,
        )


class _Harness:
    def __init__(
        self,
        *,
        provider: StubProvider | SequenceProvider,
        daily_token_limit: int = 1_000_000,
    ) -> None:
        self.conversion_jobs = InMemoryConversionHubJobRepository()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.leases = InMemoryLeaseRepository(daily_token_limit=daily_token_limit)
        self.proposed_overlays = InMemoryProposedOverlayRepository()
        self.provider = provider
        self.producer = RecordingProducer()
        self.artifacts = RecordingArtifactStore()
        vault_files = InMemoryVaultFileRepository()
        vault_storage = InMemoryVaultStorage()
        codec = ExamWorkspaceContainerCodec()
        self.handler = ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=self.enrichment_jobs,
            conversion_jobs=self.conversion_jobs,
            leases=self.leases,
            proposed_overlays=self.proposed_overlays,
            provider=provider,
            provider_selector=FixedRouteAnswerKeyProviderSelector(route=_route()),
            producer=self.producer,
            artifacts=self.artifacts,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            id_generator=UUIDGenerator(),
            vault_files=vault_files,
            vault_storage=vault_storage,
            workspace_codec=codec,
            docx_handler=docx_job_handler(
                enrichment_jobs=self.enrichment_jobs,
                proposed_overlays=self.proposed_overlays,
                leases=self.leases,
                provider=provider,
                vault_files=vault_files,
                vault_storage=vault_storage,
                codec=codec,
            ),
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
