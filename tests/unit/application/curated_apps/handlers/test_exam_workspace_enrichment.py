"""Tests for exam workspace enrichment enqueue idempotency and status reads.

Purpose:
    Prove the enqueue handler inserts exactly one workspace job per
    (lineage, revision) and stays inert when the lane is disabled or the
    document has no unkeyed keyed items, and that the status handler serves
    job states plus MACHINE_PROPOSED prefill proposals for the head revision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    EnqueueExamWorkspaceEnrichmentHandler,
    ExamWorkspaceEnrichmentState,
    GetExamWorkspaceEnrichmentStatusHandler,
)
from skriptoteket.config import Settings
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
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.test_exam_answer_key_enrichment_jobs import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    InMemoryProposedOverlayRepository,
    UUIDGenerator,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FakeWorkspaceCodec:
    def __init__(self, *, container: ExamWorkspaceContainerContent) -> None:
        self._container = container

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes:
        raise AssertionError("Status reads never rebuild containers.")

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent:
        del content
        return self._container


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.DETERMINISTIC,
    )


def _document(
    *,
    document_id: UUID,
    revision: int = 1,
    keyed: bool = False,
) -> NativeExamDocument:
    origin = NativeAnswerKeyOrigin.SOURCE_PROVIDED if keyed else NativeAnswerKeyOrigin.ABSENT
    correct = ("choice_002",) if keyed else ()
    return NativeExamDocument(
        document_id=document_id,
        revision=revision,
        title="Omprov: grammatik",
        items=(
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                title="Flervalsfråga",
                body=(
                    NativeParagraph(segments=(NativeTextSegment(text="Vilket är huvudordet?"),)),
                ),
                points=1,
                choices=(
                    NativeChoice(choice_id="choice_001", text="vägen"),
                    NativeChoice(choice_id="choice_002", text="eleverna"),
                ),
                answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct),
                review=_review(),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _enqueue_handler(
    *,
    enrichment_jobs: InMemoryEnrichmentJobRepository,
    enabled: bool = True,
) -> EnqueueExamWorkspaceEnrichmentHandler:
    return EnqueueExamWorkspaceEnrichmentHandler(
        enrichment_jobs=enrichment_jobs,
        enrichment_enabled=enabled,
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        id_generator=UUIDGenerator(),
    )


class TestEnqueue:
    async def test_enqueues_one_workspace_job_for_an_unkeyed_document(self) -> None:
        actor = make_actor()
        jobs = InMemoryEnrichmentJobRepository()
        document = _document(document_id=uuid4())

        created = await _enqueue_handler(enrichment_jobs=jobs).handle(
            actor=actor, document=document
        )

        assert created is True
        job = next(iter(jobs.jobs.values()))
        assert job.source_kind is ExamAnswerKeySourceKind.WORKSPACE
        assert job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED
        assert job.workspace_lineage_id == document.document_id
        assert job.workspace_document_revision == 1
        assert job.conversion_job_id is None
        assert job.source_dxe is None

    async def test_enqueue_is_idempotent_per_lineage_and_revision(self) -> None:
        actor = make_actor()
        jobs = InMemoryEnrichmentJobRepository()
        document = _document(document_id=uuid4())
        handler = _enqueue_handler(enrichment_jobs=jobs)

        first = await handler.handle(actor=actor, document=document)
        second = await handler.handle(actor=actor, document=document)

        assert first is True
        assert second is False
        assert len(jobs.jobs) == 1

    async def test_disabled_lane_and_keyed_documents_enqueue_nothing(self) -> None:
        actor = make_actor()
        jobs = InMemoryEnrichmentJobRepository()

        disabled = await _enqueue_handler(enrichment_jobs=jobs, enabled=False).handle(
            actor=actor, document=_document(document_id=uuid4())
        )
        keyed = await _enqueue_handler(enrichment_jobs=jobs).handle(
            actor=actor, document=_document(document_id=uuid4(), keyed=True)
        )

        assert disabled is False
        assert keyed is False
        assert jobs.jobs == {}


class _StatusHarness:
    def __init__(self, *, document: NativeExamDocument, actor_id: UUID) -> None:
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.proposed_overlays = InMemoryProposedOverlayRepository()
        self.vault_files = InMemoryVaultFileRepository()
        self.vault_storage = InMemoryVaultStorage()
        head_file_id = uuid4()
        self.vault_files.files[head_file_id] = VaultFile(
            id=head_file_id,
            user_id=actor_id,
            name="prov.provdokument.zip",
            bytes=1,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            document_lineage_id=document.document_id,
            document_version=document.revision,
            created_at=_NOW,
        )
        self.vault_storage.stored[(actor_id, head_file_id)] = b"container"
        store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=InMemoryVaultUsageRepository(
                usage=VaultUsage(user_id=actor_id, bytes_total=0, updated_at=_NOW)
            ),
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000,
                VAULT_MAX_TOTAL_BYTES=50_000_000,
            ),
        )
        self.handler = GetExamWorkspaceEnrichmentStatusHandler(
            vault_files=self.vault_files,
            enrichment_jobs=self.enrichment_jobs,
            proposed_overlays=self.proposed_overlays,
            store=store,
            codec=FakeWorkspaceCodec(container=ExamWorkspaceContainerContent(document=document)),
        )


class TestStatus:
    async def test_not_requested_without_a_job_for_the_head_revision(self) -> None:
        actor = make_actor()
        document = _document(document_id=uuid4())
        harness = _StatusHarness(document=document, actor_id=actor.id)

        response = await harness.handler.handle(actor=actor, lineage_id=document.document_id)

        assert response.state is ExamWorkspaceEnrichmentState.NOT_REQUESTED
        assert response.document_revision == 1
        assert response.proposals == ()

    async def test_succeeded_job_serves_machine_proposed_prefill_items(self) -> None:
        actor = make_actor()
        document = _document(document_id=uuid4())
        harness = _StatusHarness(document=document, actor_id=actor.id)

        created = await _enqueue_handler(enrichment_jobs=harness.enrichment_jobs).handle(
            actor=actor, document=document
        )
        assert created is True
        job = next(iter(harness.enrichment_jobs.jobs.values()))
        harness.enrichment_jobs.jobs[job.id] = job.model_copy(
            update={"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED}
        )
        await harness.proposed_overlays.create(
            proposed_overlay=ExamAnswerKeyProposedOverlay(
                id=uuid4(),
                enrichment_job_id=job.id,
                conversion_job_id=None,
                owner_user_id=actor.id,
                workspace_lineage_id=document.document_id,
                workspace_document_revision=1,
                source_file_sha256="a" * 64,
                source_ir_sha256="b" * 64,
                provider_profile_id="openai-gpt-5.6-luna",
                model="gpt-5.6-luna",
                overlay_json={
                    "schema_version": EXAM_WORKSPACE_ANSWER_KEY_PROPOSALS_SCHEMA_VERSION,
                    "lineage_id": str(document.document_id),
                    "document_revision": 1,
                    "items": [
                        {
                            "item_id": "item_001",
                            "kind": "choice",
                            "correct_choice_ids": ["choice_002"],
                            "gap_accepted_values": {},
                            "provider_profile_id": "openai-gpt-5.6-luna",
                            "model": "gpt-5.6-luna",
                            "prompt_template_version": "digiexam_choice_answer_key_prompt_v1",
                        }
                    ],
                },
                created_at=_NOW,
            )
        )

        response = await harness.handler.handle(actor=actor, lineage_id=document.document_id)

        assert response.state is ExamWorkspaceEnrichmentState.SUCCEEDED
        assert len(response.proposals) == 1
        proposal = response.proposals[0]
        assert proposal.item_id == "item_001"
        assert proposal.provider_profile_id == "openai-gpt-5.6-luna"
        proposed = proposal.proposed_item
        assert proposed.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
        assert proposed.answer_key.correct_choice_ids == ("choice_002",)
        assert proposed.review.state is NativeItemReviewState.REVIEW_REQUIRED

    async def test_failed_job_maps_last_error_to_a_swedish_message(self) -> None:
        actor = make_actor()
        document = _document(document_id=uuid4())
        harness = _StatusHarness(document=document, actor_id=actor.id)
        created = await _enqueue_handler(enrichment_jobs=harness.enrichment_jobs).handle(
            actor=actor, document=document
        )
        assert created is True
        job = next(iter(harness.enrichment_jobs.jobs.values()))
        harness.enrichment_jobs.jobs[job.id] = job.model_copy(
            update={
                "status": ExamAnswerKeyEnrichmentJobStatus.FAILED,
                "last_error": "daily_token_lease_exhausted",
            }
        )

        response = await harness.handler.handle(actor=actor, lineage_id=document.document_id)

        assert response.state is ExamWorkspaceEnrichmentState.FAILED
        assert response.message is not None
        assert "AI-budget" in response.message

    async def test_queued_job_reports_queued_state(self) -> None:
        actor = make_actor()
        document = _document(document_id=uuid4())
        harness = _StatusHarness(document=document, actor_id=actor.id)
        created = await _enqueue_handler(enrichment_jobs=harness.enrichment_jobs).handle(
            actor=actor, document=document
        )
        assert created is True

        response = await harness.handler.handle(actor=actor, lineage_id=document.document_id)

        assert response.state is ExamWorkspaceEnrichmentState.QUEUED
