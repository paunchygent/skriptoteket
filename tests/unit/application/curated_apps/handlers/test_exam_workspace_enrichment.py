"""Tests for exam workspace answer-key suggestion requests and status reads.

Purpose:
    Prove a request runs on the editor-sent content (TASK-SKRIPT-39-04-07):
    "suggest for all" sends every keyed-kind question without a key, a
    per-question request sends one question with or without a key, and the
    status read returns the suggestions stored on the finished job only to
    the job's owner.
"""

from __future__ import annotations

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
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
)
from skriptoteket.domain.errors import DomainError
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    NOW,
    SuggestionHandlerHarness,
    suggestion_document,
    suggestion_item,
)

pytestmark = pytest.mark.unit


class TestRequest:
    async def test_suggest_for_all_skips_keyed_questions(self) -> None:
        harness = SuggestionHandlerHarness()
        document = suggestion_document(
            harness.lineage_id,
            suggestion_item(item_id="item_001", sequence=1),
            suggestion_item(
                item_id="item_002",
                sequence=2,
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
            ),
            suggestion_item(item_id="item_003", sequence=3),
        )

        response = await harness.request(document)

        assert response.state is ExamWorkspaceEnrichmentState.QUEUED
        assert response.job_id is not None
        job = harness.jobs.jobs[response.job_id]
        assert job.source_kind is ExamAnswerKeySourceKind.WORKSPACE
        assert job.workspace_lineage_id == harness.lineage_id
        # The job records the saved version the editor's copy stood on.
        assert job.workspace_document_revision == document.revision == 3
        payload = WorkspaceAnswerKeyRequestPayload.model_validate(job.workspace_request_json)
        assert [view.item_id for view in payload.views] == ["item_001", "item_003"]

    async def test_per_question_request_uses_unsaved_sent_content(self) -> None:
        harness = SuggestionHandlerHarness()
        # The saved head is revision 3; the editor sends edited, unsaved
        # wording for a question that already carries a teacher key.
        document = suggestion_document(
            harness.lineage_id,
            suggestion_item(
                item_id="item_001",
                sequence=1,
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                stem="Vilket är subjektet i meningen?",
            ),
        )

        response = await harness.request(document, item_id="item_001")

        assert response.state is ExamWorkspaceEnrichmentState.QUEUED
        assert response.job_id is not None
        job = harness.jobs.jobs[response.job_id]
        payload = WorkspaceAnswerKeyRequestPayload.model_validate(job.workspace_request_json)
        assert len(payload.views) == 1
        assert payload.views[0].stem_text == "Vilket är subjektet i meningen?"

    async def test_disabled_lane_and_all_keyed_documents_enqueue_nothing(self) -> None:
        document = suggestion_document(
            uuid4(),
            suggestion_item(
                item_id="item_001",
                sequence=1,
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            ),
        )
        disabled = SuggestionHandlerHarness(enabled=False)
        disabled.lineage_id = document.document_id
        keyed = SuggestionHandlerHarness()
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
        harness = SuggestionHandlerHarness()
        document = suggestion_document(uuid4(), suggestion_item(item_id="item_001", sequence=1))

        with pytest.raises(DomainError):
            await harness.request_handler.handle(
                actor=harness.actor,
                lineage_id=document.document_id,
                request=RequestExamWorkspaceAnswerKeySuggestionsRequest(document=document),
            )
        assert harness.jobs.jobs == {}


class TestStatus:
    async def _finished_job(self, harness: SuggestionHandlerHarness, *, succeeded: bool) -> UUID:
        document = suggestion_document(
            harness.lineage_id, suggestion_item(item_id="item_001", sequence=1)
        )
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
        harness = SuggestionHandlerHarness()
        job_id = await self._finished_job(harness, succeeded=True)

        response = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=job_id
        )

        assert response.state is ExamWorkspaceEnrichmentState.SUCCEEDED
        assert len(response.suggestions) == 1
        assert response.suggestions[0].item_id == "item_001"
        assert response.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)
        assert response.suggestions[0].suggestion.model == "gpt-5.6-luna"

    async def test_failed_job_returns_suggestions_it_produced_before_the_failure(self) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await self._finished_job(harness, succeeded=True)
        job = harness.jobs.jobs[job_id]
        harness.jobs.jobs[job_id] = job.model_copy(
            update={
                "status": ExamAnswerKeyEnrichmentJobStatus.FAILED,
                "last_error": "provider_timeout",
            }
        )

        response = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=job_id
        )

        assert response.state is ExamWorkspaceEnrichmentState.FAILED
        assert response.message is not None
        assert [entry.item_id for entry in response.suggestions] == ["item_001"]
        assert response.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)

    async def test_failed_job_maps_last_error_to_a_swedish_message(self) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await self._finished_job(harness, succeeded=False)

        response = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=job_id
        )

        assert response.state is ExamWorkspaceEnrichmentState.FAILED
        assert response.message is not None
        assert "AI-budget" in response.message

    async def test_status_is_hidden_from_other_teachers(self) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await self._finished_job(harness, succeeded=True)

        with pytest.raises(DomainError):
            await harness.status_handler.handle(
                actor=make_actor(), lineage_id=harness.lineage_id, job_id=job_id
            )

    async def test_queued_job_reports_queued_state(self) -> None:
        harness = SuggestionHandlerHarness()
        document = suggestion_document(
            harness.lineage_id, suggestion_item(item_id="item_001", sequence=1)
        )
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
        workspace_document_revision=4,
        workspace_request_json={"views": []},
        now=NOW,
    )
    assert job.workspace_document_revision == 4
    assert job.workspace_request_json == {"views": []}
