"""Workspace-lane worker tests for machine answer-key enrichment.

Purpose:
    Prove the workspace branch of the enrichment processor: the pinned head
    container is loaded through the vault seams, the same lease discipline
    runs (reserve before the call, reconcile from usage), a native-shaped
    proposals payload is persisted, and the conversion producer is never
    called. Failure paths finish the job without touching conversion jobs.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against in-memory protocol fakes mirroring
      `test_exam_answer_key_enrichment_jobs` (the DXE lane stays untouched).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    EXAM_WORKSPACE_ANSWER_KEY_PROPOSALS_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
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
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.test_exam_answer_key_enrichment_jobs import (
    FixedClock,
    InMemoryConversionHubJobRepository,
    InMemoryEnrichmentJobRepository,
    InMemoryLeaseRepository,
    InMemoryProposedOverlayRepository,
    RecordingArtifactStore,
    StubProvider,
    UUIDGenerator,
    _route,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class CountingProducer:
    """DXE-only producer double that must never be called on this lane."""

    def __init__(self) -> None:
        self.calls = 0

    async def convert(self, **kwargs: object) -> None:
        self.calls += 1
        raise AssertionError("Workspace enrichment must never call the conversion producer.")


class FakeVaultFiles:
    def __init__(self) -> None:
        self.heads: dict[UUID, VaultFile] = {}

    async def get_document_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> VaultFile | None:
        head = self.heads.get(document_lineage_id)
        if head is None or head.user_id != user_id:
            return None
        return head


class FakeVaultStorage:
    def __init__(self) -> None:
        self.contents: dict[UUID, bytes] = {}

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        del user_id
        return self.contents[file_id]


class FakeWorkspaceCodec:
    def __init__(self, *, container: ExamWorkspaceContainerContent) -> None:
        self._container = container

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes:
        raise AssertionError("The worker never rebuilds containers.")

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent:
        del content
        return self._container


def _unkeyed_choice_document(*, document_id: UUID, revision: int) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=document_id,
        revision=revision,
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
        head_revision: int | None = None,
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
        self.vault_files = FakeVaultFiles()
        self.vault_storage = FakeVaultStorage()
        self.document = document
        self.container_bytes = b"container-bytes"

        head_file_id = uuid4()
        self.vault_files.heads[document.document_id] = VaultFile(
            id=head_file_id,
            user_id=self.owner_user_id,
            name="prov.provdokument.zip",
            bytes=len(self.container_bytes),
            source_kind=VaultFileSourceKind.APP_EXPORT,
            document_lineage_id=document.document_id,
            document_version=head_revision if head_revision is not None else document.revision,
            created_at=_NOW,
        )
        self.vault_storage.contents[head_file_id] = self.container_bytes

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
            vault_files=self.vault_files,
            vault_storage=self.vault_storage,
            workspace_codec=FakeWorkspaceCodec(
                container=ExamWorkspaceContainerContent(document=document)
            ),
        )

    async def seed_claimed_job(self) -> ExamAnswerKeyEnrichmentJob:
        await self.enrichment_jobs.create(
            job=enqueue_workspace_enrichment_job(
                job_id=uuid4(),
                owner_user_id=self.owner_user_id,
                input_filename=self.document.title,
                workspace_lineage_id=self.document.document_id,
                workspace_document_revision=self.document.revision,
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


async def test_workspace_job_persists_proposals_without_calling_the_producer() -> None:
    document = _unkeyed_choice_document(document_id=uuid4(), revision=1)
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
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 190

    proposal = harness.proposed_overlays.records[0]
    assert proposal.enrichment_job_id == job.id
    assert proposal.conversion_job_id is None
    assert proposal.workspace_lineage_id == document.document_id
    assert proposal.workspace_document_revision == 1
    assert proposal.provider_profile_id == "openai-gpt-5.6-luna"
    payload = proposal.overlay_json
    assert payload["schema_version"] == EXAM_WORKSPACE_ANSWER_KEY_PROPOSALS_SCHEMA_VERSION
    assert payload["lineage_id"] == str(document.document_id)
    assert payload["document_revision"] == 1
    items = payload["items"]
    assert isinstance(items, list)
    assert items[0]["item_id"] == "item_001"
    assert items[0]["correct_choice_ids"] == ["choice_002"]
    assert items[0]["prompt_template_version"] == "digiexam_choice_answer_key_prompt_v1"


async def test_workspace_lease_refusal_fails_closed_with_zero_provider_calls() -> None:
    document = _unkeyed_choice_document(document_id=uuid4(), revision=1)
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


async def test_workspace_job_fails_when_head_revision_moved_on() -> None:
    document = _unkeyed_choice_document(document_id=uuid4(), revision=1)
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _WorkspaceHarness(provider=provider, document=document, head_revision=2)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "workspace_document_revision_stale"
    assert harness.proposed_overlays.records == []


async def test_invalid_workspace_model_output_fails_without_a_proposal() -> None:
    document = _unkeyed_choice_document(document_id=uuid4(), revision=1)
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
    leases = list(harness.leases.leases.values())
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert harness.proposed_overlays.records == []
    assert harness.producer.calls == 0
