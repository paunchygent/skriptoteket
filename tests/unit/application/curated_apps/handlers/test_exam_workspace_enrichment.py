"""Tests for exam workspace answer-key suggestion requests and status reads.

Purpose:
    Prove a request runs on the editor-sent content (TASK-SKRIPT-39-04-07):
    "suggest for all" sends every keyed-kind question without a key, a
    per-question request sends one question with or without a key, and the
    status read returns the suggestions stored on the finished job only to
    the job's owner.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceEnrichmentState,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    GetExamWorkspaceAnswerKeySuggestionsStatusHandler,
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
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
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    UUIDGenerator,
)
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


def _item(
    *,
    item_id: str,
    sequence: int,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.ABSENT,
    stem: str = "Vilket är huvudordet?",
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(NativeParagraph(segments=(NativeTextSegment(text=stem),)),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            correct_choice_ids=("choice_001",)
            if origin is not NativeAnswerKeyOrigin.ABSENT
            else (),
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.TEACHER_CREATED,
        ),
    )


def _document(document_id: UUID, *items: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=document_id,
        revision=3,
        title="Omprov: grammatik",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class _Harness:
    def __init__(self, *, enabled: bool = True) -> None:
        self.actor = make_actor()
        self.jobs = InMemoryEnrichmentJobRepository()
        self.vault_files = InMemoryVaultFileRepository()
        self.lineage_id = uuid4()
        head_id = uuid4()
        self.vault_files.files[head_id] = VaultFile(
            id=head_id,
            user_id=self.actor.id,
            name="prov.provdokument.zip",
            bytes=1,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            document_lineage_id=self.lineage_id,
            document_version=3,
            created_at=_NOW,
        )
        self.request_handler = RequestExamWorkspaceAnswerKeySuggestionsHandler(
            enrichment_jobs=self.jobs,
            enrichment_enabled=enabled,
            vault_files=self.vault_files,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            id_generator=UUIDGenerator(),
        )
        self.status_handler = GetExamWorkspaceAnswerKeySuggestionsStatusHandler(
            enrichment_jobs=self.jobs,
        )

    async def request(self, document: NativeExamDocument, item_id: str | None = None) -> object:
        return await self.request_handler.handle(
            actor=self.actor,
            lineage_id=self.lineage_id,
            request=RequestExamWorkspaceAnswerKeySuggestionsRequest(
                document=document, item_id=item_id
            ),
        )


class TestRequest:
    async def test_suggest_for_all_skips_keyed_questions(self) -> None:
        harness = _Harness()
        document = _document(
            harness.lineage_id,
            _item(item_id="item_001", sequence=1),
            _item(
                item_id="item_002",
                sequence=2,
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
            ),
            _item(item_id="item_003", sequence=3),
        )

        response = await harness.request(document)

        assert response.state is ExamWorkspaceEnrichmentState.QUEUED
        assert response.job_id is not None
        job = harness.jobs.jobs[response.job_id]
        assert job.source_kind is ExamAnswerKeySourceKind.WORKSPACE
        assert job.workspace_lineage_id == harness.lineage_id
        assert job.workspace_document_revision is None
        payload = WorkspaceAnswerKeyRequestPayload.model_validate(job.workspace_request_json)
        assert [view.item_id for view in payload.views] == ["item_001", "item_003"]

    async def test_per_question_request_uses_unsaved_sent_content(self) -> None:
        harness = _Harness()
        # The saved head is revision 3; the editor sends edited, unsaved
        # wording for a question that already carries a teacher key.
        document = _document(
            harness.lineage_id,
            _item(
                item_id="item_001",
                sequence=1,
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                stem="Vilket är subjektet i meningen?",
            ),
        )

        response = await harness.request(document, item_id="item_001")

        assert response.state is ExamWorkspaceEnrichmentState.QUEUED
        job = harness.jobs.jobs[response.job_id]
        payload = WorkspaceAnswerKeyRequestPayload.model_validate(job.workspace_request_json)
        assert len(payload.views) == 1
        assert payload.views[0].stem_text == "Vilket är subjektet i meningen?"

    async def test_disabled_lane_and_all_keyed_documents_enqueue_nothing(self) -> None:
        document = _document(
            uuid4(),
            _item(
                item_id="item_001",
                sequence=1,
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            ),
        )
        disabled = _Harness(enabled=False)
        disabled.lineage_id = document.document_id
        keyed = _Harness()
        keyed.lineage_id = document.document_id
        for harness in (disabled, keyed):
            head = next(iter(harness.vault_files.files.values()))
            harness.vault_files.files[head.id] = head.model_copy(
                update={"document_lineage_id": document.document_id}
            )

        for harness in (disabled, keyed):
            response = await harness.request_handler.handle(
                actor=harness.actor,
                lineage_id=document.document_id,
                request=RequestExamWorkspaceAnswerKeySuggestionsRequest(document=document),
            )
            assert response.state is ExamWorkspaceEnrichmentState.NOT_ELIGIBLE
            assert response.job_id is None
        assert disabled.jobs.jobs == {}
        assert keyed.jobs.jobs == {}

    async def test_request_for_another_teachers_document_is_not_found(self) -> None:
        harness = _Harness()
        document = _document(uuid4(), _item(item_id="item_001", sequence=1))

        with pytest.raises(DomainError):
            await harness.request_handler.handle(
                actor=harness.actor,
                lineage_id=document.document_id,
                request=RequestExamWorkspaceAnswerKeySuggestionsRequest(document=document),
            )
        assert harness.jobs.jobs == {}


class TestStatus:
    async def _finished_job(self, harness: _Harness, *, succeeded: bool) -> UUID:
        document = _document(harness.lineage_id, _item(item_id="item_001", sequence=1))
        response = await harness.request(document)
        assert response.job_id is not None
        job = harness.jobs.jobs[response.job_id]
        if succeeded:
            suggestion = NativeAnswerKeySuggestion(
                correct_choice_ids=("choice_002",),
                fingerprint="a" * 64,
                provider_profile_id="openai-gpt-5.6-luna",
                model="gpt-5.6-luna",
                prompt_template_version="v1",
            )
            harness.jobs.jobs[job.id] = job.model_copy(
                update={
                    "status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    "workspace_suggestions_json": {
                        "suggestions": [
                            {
                                "item_id": "item_001",
                                "suggestion": suggestion.model_dump(mode="json"),
                            }
                        ]
                    },
                }
            )
        else:
            harness.jobs.jobs[job.id] = job.model_copy(
                update={
                    "status": ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    "last_error": "daily_token_lease_exhausted",
                }
            )
        return job.id

    async def test_succeeded_job_returns_its_suggestions(self) -> None:
        harness = _Harness()
        job_id = await self._finished_job(harness, succeeded=True)

        response = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=job_id
        )

        assert response.state is ExamWorkspaceEnrichmentState.SUCCEEDED
        assert len(response.suggestions) == 1
        assert response.suggestions[0].item_id == "item_001"
        assert response.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)
        assert response.suggestions[0].suggestion.model == "gpt-5.6-luna"

    async def test_failed_job_maps_last_error_to_a_swedish_message(self) -> None:
        harness = _Harness()
        job_id = await self._finished_job(harness, succeeded=False)

        response = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=job_id
        )

        assert response.state is ExamWorkspaceEnrichmentState.FAILED
        assert response.message is not None
        assert "AI-budget" in response.message

    async def test_status_is_hidden_from_other_teachers(self) -> None:
        harness = _Harness()
        job_id = await self._finished_job(harness, succeeded=True)

        with pytest.raises(DomainError):
            await harness.status_handler.handle(
                actor=make_actor(), lineage_id=harness.lineage_id, job_id=job_id
            )

    async def test_queued_job_reports_queued_state(self) -> None:
        harness = _Harness()
        document = _document(harness.lineage_id, _item(item_id="item_001", sequence=1))
        response = await harness.request(document)
        assert response.job_id is not None

        status = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=response.job_id
        )

        assert status.state is ExamWorkspaceEnrichmentState.QUEUED
        assert status.suggestions == ()


def test_enqueue_helper_builds_an_editor_content_job() -> None:
    job = enqueue_workspace_enrichment_job(
        job_id=uuid4(),
        owner_user_id=uuid4(),
        input_filename="Prov",
        workspace_lineage_id=uuid4(),
        workspace_request_json={"views": []},
        now=_NOW,
    )
    assert job.workspace_document_revision is None
    assert job.workspace_request_json == {"views": []}
