"""Tests for finding a lost suggestion job and reusing a running one.

Purpose:
    Prove TASK-SKRIPT-39-04-09 P1-P3 at the handlers: an exam opened again
    finds the newest suggestion job requested on its current saved version,
    mapped exactly as the status read maps it; a job on an older saved
    version, another teacher's job, another exam's job and a DOCX import job
    are never found; and a request repeating a queued or running job's exact
    content on the same saved version gets that job back without a new job.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceEnrichmentState
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
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


async def _requested(harness: SuggestionHandlerHarness, item_id: str = "item_001") -> UUID:
    document = suggestion_document(harness.lineage_id, suggestion_item(item_id=item_id, sequence=1))
    response = await harness.request(document)
    assert response.job_id is not None
    return response.job_id


def _set(harness: SuggestionHandlerHarness, job_id: UUID, **update: object) -> None:
    job = harness.jobs.jobs[job_id]
    harness.jobs.jobs[job_id] = ExamAnswerKeyEnrichmentJob.model_validate(
        {**job.model_dump(), **update}
    )


def _succeeded(harness: SuggestionHandlerHarness, job_id: UUID, choice_id: str) -> None:
    suggestion = NativeAnswerKeySuggestion(
        correct_choice_ids=(choice_id,),
        fingerprint="a" * 64,
        provider_profile_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        prompt_template_version="v1",
    )
    _set(
        harness,
        job_id,
        status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
        workspace_suggestions_json={
            "suggestions": [
                {"item_id": "item_001", "suggestion": suggestion.model_dump(mode="json")}
            ]
        },
    )


class TestFind:
    async def test_newest_job_on_the_current_saved_version_is_found(self) -> None:
        harness = SuggestionHandlerHarness()
        older = await _requested(harness)
        _succeeded(harness, older, "choice_001")
        newer = await _requested(harness, item_id="item_002")
        _succeeded(harness, newer, "choice_002")
        _set(harness, newer, created_at=NOW + timedelta(seconds=5))

        found = await harness.find_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, document_revision=3
        )
        status = await harness.status_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, job_id=newer
        )

        assert found is not None
        assert found.job_id == newer
        assert found.state is ExamWorkspaceEnrichmentState.SUCCEEDED
        assert found == status

    @pytest.mark.parametrize(
        "status",
        [ExamAnswerKeyEnrichmentJobStatus.QUEUED, ExamAnswerKeyEnrichmentJobStatus.RUNNING],
    )
    async def test_pending_job_is_found_with_its_state(
        self, status: ExamAnswerKeyEnrichmentJobStatus
    ) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await _requested(harness)
        _set(harness, job_id, status=status)

        found = await harness.find_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, document_revision=3
        )

        assert found is not None
        assert found.job_id == job_id
        assert found.state.value == status.value
        assert found.suggestions == ()

    async def test_failed_job_is_found_with_its_partial_suggestions_and_message(self) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await _requested(harness)
        _succeeded(harness, job_id, "choice_002")
        _set(
            harness,
            job_id,
            status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
            last_error="daily_token_lease_exhausted",
        )

        found = await harness.find_handler.handle(
            actor=harness.actor, lineage_id=harness.lineage_id, document_revision=3
        )

        assert found is not None
        assert found.state is ExamWorkspaceEnrichmentState.FAILED
        assert found.message is not None and "AI-budget" in found.message
        assert [entry.item_id for entry in found.suggestions] == ["item_001"]

    async def test_job_on_an_older_saved_version_is_never_found(self) -> None:
        harness = SuggestionHandlerHarness()
        job_id = await _requested(harness)
        _set(harness, job_id, workspace_document_revision=2)

        assert (
            await harness.find_handler.handle(
                actor=harness.actor, lineage_id=harness.lineage_id, document_revision=3
            )
            is None
        )

    async def test_copy_older_than_the_saved_head_finds_nothing(self) -> None:
        # The job stands on revision 2 and the editor asks for revision 2,
        # but the exam has been saved again as revision 3 since.
        harness = SuggestionHandlerHarness()
        job_id = await _requested(harness)
        _set(harness, job_id, workspace_document_revision=2)

        assert (
            await harness.find_handler.handle(
                actor=harness.actor, lineage_id=harness.lineage_id, document_revision=2
            )
            is None
        )

    async def test_other_owner_lineage_and_lane_are_not_found(self) -> None:
        harness = SuggestionHandlerHarness()
        foreign = await _requested(harness)
        _set(harness, foreign, owner_user_id=make_actor().id)
        other_exam = await _requested(harness)
        _set(harness, other_exam, workspace_lineage_id=uuid4())
        docx = await _requested(harness)
        _set(
            harness,
            docx,
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            workspace_request_json=None,
            workspace_document_revision=1,
            status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
        )

        assert (
            await harness.find_handler.handle(
                actor=harness.actor, lineage_id=harness.lineage_id, document_revision=3
            )
            is None
        )

    async def test_another_teachers_exam_is_not_found(self) -> None:
        harness = SuggestionHandlerHarness()
        await _requested(harness)

        with pytest.raises(DomainError):
            await harness.find_handler.handle(
                actor=make_actor(), lineage_id=harness.lineage_id, document_revision=3
            )


class TestReuse:
    @pytest.mark.parametrize(
        "status",
        [ExamAnswerKeyEnrichmentJobStatus.QUEUED, ExamAnswerKeyEnrichmentJobStatus.RUNNING],
    )
    async def test_same_questions_on_the_same_version_return_the_pending_job(
        self, status: ExamAnswerKeyEnrichmentJobStatus
    ) -> None:
        harness = SuggestionHandlerHarness()
        first = await _requested(harness)
        _set(harness, first, status=status)

        again = await harness.request(
            suggestion_document(harness.lineage_id, suggestion_item(item_id="item_001", sequence=1))
        )

        assert again.job_id == first
        assert again.state.value == status.value
        assert list(harness.jobs.jobs) == [first]

    async def test_per_question_request_reuses_a_pending_job_on_the_same_question(self) -> None:
        harness = SuggestionHandlerHarness()
        document = suggestion_document(
            harness.lineage_id, suggestion_item(item_id="item_001", sequence=1)
        )
        first = await harness.request(document, item_id="item_001")

        again = await harness.request(document, item_id="item_001")

        assert first.job_id is not None and again.job_id == first.job_id
        assert len(harness.jobs.jobs) == 1

    async def test_finished_job_is_not_reused(self) -> None:
        harness = SuggestionHandlerHarness()
        first = await _requested(harness)
        _succeeded(harness, first, "choice_001")

        again = await _requested(harness)

        assert again != first
        assert harness.jobs.jobs[again].status is ExamAnswerKeyEnrichmentJobStatus.QUEUED

    async def test_other_questions_start_a_new_job(self) -> None:
        harness = SuggestionHandlerHarness()
        first = await _requested(harness, item_id="item_001")

        second = await _requested(harness, item_id="item_002")

        assert second != first
        assert len(harness.jobs.jobs) == 2

    async def test_edited_question_content_starts_a_new_job(self) -> None:
        harness = SuggestionHandlerHarness()
        first = await _requested(harness)

        edited = await harness.request(
            suggestion_document(
                harness.lineage_id,
                suggestion_item(item_id="item_001", sequence=1, stem="Vilket är subjektet?"),
            )
        )

        assert edited.job_id is not None and edited.job_id != first
        assert len(harness.jobs.jobs) == 2

    async def test_same_content_on_another_saved_version_starts_a_new_job(self) -> None:
        harness = SuggestionHandlerHarness()
        first = await _requested(harness)
        _set(harness, first, workspace_document_revision=2)

        second = await _requested(harness)

        assert second != first
        assert harness.jobs.jobs[second].workspace_document_revision == 3
