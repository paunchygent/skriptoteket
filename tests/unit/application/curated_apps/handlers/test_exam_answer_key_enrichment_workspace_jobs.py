"""Workspace-lane worker tests for AI answer-key suggestions.

Purpose:
    Prove the workspace branch of the enrichment processor runs on the
    answer-key views sent with the job (TASK-SKRIPT-39-04-07), never on a
    saved revision: the same lease discipline runs (reserve before the
    call, reconcile from usage), the suggestions are stored on the job
    itself with their fingerprints and provider lineage, no overlay is
    written, and the conversion producer is never called. Failure paths
    finish the job without touching conversion jobs.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against the shared in-memory protocol fakes in
      `answer_key_enrichment_test_support` (the DXE lane stays untouched).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionStoredArtifact,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
    WorkspaceAnswerKeySuggestionsPayload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    SourceBoundCorrectionIntent,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint,
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
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
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    document_of,
    recorded_matching_items,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


class CountingProducer:
    """DXE-only producer double that must never be called on this lane."""

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
        self.calls += 1
        raise AssertionError("Workspace enrichment must never call the conversion producer.")


def _unkeyed_choice_document(*, document_id: UUID) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=document_id,
        revision=7,
        title="Omprov utan facit",
        items=(
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                title="Flervalsfråga",
                body=(
                    NativeParagraph(
                        segments=(NativeTextSegment(text="Välj den grekiska bokstaven."),)
                    ),
                ),
                points=2,
                choices=(
                    NativeChoice(choice_id="choice_001", text="Alfa"),
                    NativeChoice(choice_id="choice_002", text="Beta"),
                ),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
                review=NativeItemReview(
                    state=NativeItemReviewState.REVIEW_COMPLETE,
                    parse_origin=NativeParseOrigin.DETERMINISTIC,
                ),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class _WorkspaceHarness:
    def __init__(
        self,
        *,
        provider: StubProvider,
        document: NativeExamDocument,
        daily_token_limit: int = 1_000_000,
    ) -> None:
        self.owner_user_id = uuid4()
        self.conversion_jobs = InMemoryConversionHubJobRepository()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.leases = InMemoryLeaseRepository(daily_token_limit=daily_token_limit)
        self.proposed_overlays = InMemoryProposedOverlayRepository()
        self.provider = provider
        self.producer = CountingProducer()
        self.artifacts = RecordingArtifactStore()
        self.document = document

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

    async def seed_claimed_job(self) -> ExamAnswerKeyEnrichmentJob:
        views = answer_key_item_views(self.document)
        await self.enrichment_jobs.create(
            job=enqueue_workspace_enrichment_job(
                job_id=uuid4(),
                owner_user_id=self.owner_user_id,
                input_filename=self.document.title,
                workspace_lineage_id=self.document.document_id,
                workspace_request_json=WorkspaceAnswerKeyRequestPayload(views=views).model_dump(
                    mode="json"
                ),
                now=_NOW,
            )
        )
        claimed = await self.enrichment_jobs.claim_next(
            worker_id="worker-1",
            now=_NOW,
            lease_ttl=timedelta(seconds=900),
        )
        assert claimed is not None
        assert claimed.source_kind is ExamAnswerKeySourceKind.WORKSPACE
        return claimed


async def test_workspace_job_stores_suggestions_on_the_job_without_an_overlay() -> None:
    document = _unkeyed_choice_document(document_id=uuid4())
    harness = _WorkspaceHarness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1
    assert harness.producer.calls == 0
    assert harness.conversion_jobs.jobs == {}
    assert harness.proposed_overlays.records == []
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 190

    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert len(payload.suggestions) == 1
    arrived = payload.suggestions[0]
    assert arrived.item_id == "item_001"
    assert arrived.suggestion.correct_choice_ids == ("choice_002",)
    assert arrived.suggestion.provider_profile_id == "openai-gpt-5.6-luna"
    assert arrived.suggestion.model == "gpt-5.6-luna"
    assert arrived.suggestion.prompt_template_version == "digiexam_choice_answer_key_prompt_v1"
    assert arrived.suggestion.fingerprint == answer_key_fingerprint(document.items[0], None)


class _SequenceProvider(StubProvider):
    """Provider double answering each call with the next scripted content."""

    def __init__(self, contents: list[dict[str, JsonValue]]) -> None:
        super().__init__(content={}, usage=StructuredLLMUsage(total_tokens=50))
        self._contents = contents

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del request, profile
        self.call_count += 1
        return StructuredLLMResponse(
            content=self._contents[self.call_count - 1],
            finish_reason="completed",
            usage=StructuredLLMUsage(total_tokens=50),
        )


def _three_unkeyed_choice_document(*, document_id: UUID) -> NativeExamDocument:
    document = _unkeyed_choice_document(document_id=document_id)
    first = document.items[0]
    items = tuple(
        first.model_copy(update={"item_id": f"item_{index:03d}", "sequence": index})
        for index in (1, 2, 3)
    )
    return document.model_copy(update={"items": items})


async def test_one_invalid_answer_keeps_valid_answers_and_continues_to_later_questions() -> None:
    document = _three_unkeyed_choice_document(document_id=uuid4())
    provider = _SequenceProvider(
        [
            {"correct_alternative_ids": [2]},
            {"correct_alternative_ids": [9]},
            {"correct_alternative_ids": [1]},
        ]
    )
    harness = _WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert provider.call_count == 3
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001", "item_003"]
    assert payload.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)
    assert payload.suggestions[1].suggestion.correct_choice_ids == ("choice_001",)
    assert harness.proposed_overlays.records == []
    assert harness.producer.calls == 0


async def test_workspace_lease_refusal_fails_closed_with_zero_provider_calls() -> None:
    document = _unkeyed_choice_document(document_id=uuid4())
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _WorkspaceHarness(provider=provider, document=document, daily_token_limit=10)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "daily_token_lease_exhausted"
    assert harness.producer.calls == 0
    assert harness.proposed_overlays.records == []


async def test_workspace_job_without_sent_content_fails_closed() -> None:
    document = _unkeyed_choice_document(document_id=uuid4())
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()
    harness.enrichment_jobs.jobs[job.id] = job.model_copy(update={"workspace_request_json": None})

    finished = await harness.handler.handle(job=harness.enrichment_jobs.jobs[job.id])

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "workspace_request_missing"


async def test_invalid_workspace_model_output_fails_without_a_suggestion() -> None:
    document = _unkeyed_choice_document(document_id=uuid4())
    harness = _WorkspaceHarness(
        provider=StubProvider(
            content={"correct_alternative_ids": [9]},
            usage=StructuredLLMUsage(total_tokens=50),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
    assert finished.workspace_suggestions_json is None
    leases = list(harness.leases.leases.values())
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert harness.proposed_overlays.records == []
    assert harness.producer.calls == 0


async def test_matching_workspace_job_stores_pairs_for_recorded_unkeyed_items() -> None:
    items = recorded_matching_items()
    document = document_of(*items)
    harness = _WorkspaceHarness(
        provider=StubProvider(
            content={
                "pairs": [
                    {"left_id": 1, "right_id": 3},
                    {"left_id": 2, "right_id": 2},
                    {"left_id": 3, "right_id": 1},
                ]
            },
            usage=StructuredLLMUsage(total_tokens=120),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == len(items)
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == [item.item_id for item in items]
    for entry in payload.suggestions:
        assert [(p.left_id, p.right_id) for p in entry.suggestion.match_pairs] == [
            ("left_001", "right_003"),
            ("left_002", "right_002"),
            ("left_003", "right_001"),
        ]
        assert entry.suggestion.prompt_template_version == "workspace_matching_answer_key_prompt_v1"


async def test_matching_workspace_job_fails_when_a_left_entry_is_left_unpaired() -> None:
    document = document_of(*recorded_matching_items())
    harness = _WorkspaceHarness(
        provider=StubProvider(
            content={"pairs": [{"left_id": 1, "right_id": 3}, {"left_id": 2, "right_id": 2}]},
            usage=StructuredLLMUsage(total_tokens=120),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
    assert harness.proposed_overlays.records == []
