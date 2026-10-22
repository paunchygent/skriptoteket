"""Fake-model worker proof on real DigiExam parser output, not live model behavior."""

import json
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionItem,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeySuggestionsPayload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import answer_key_fingerprint
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.exam_answer_key import StructuredLLMTextObserver
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    StubProvider,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    WorkspaceHarness,
)
from tests.unit.application.curated_apps.test_exam_workspace_digiexam_suggestions import (
    imported_document,
)

pytestmark = pytest.mark.unit


class CapturingModel(StubProvider):
    """Distinct item-local answers make any cross-question placement visible."""

    def __init__(self) -> None:
        super().__init__(content={}, usage=StructuredLLMUsage(total_tokens=17))
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        self.call_count += 1
        payload = json.loads(request.user_payload)
        content: dict[str, JsonValue]
        if request.item_type == "gap_fill":
            content = {
                str(gap["gap_number"]): f"{request.item_id}-svar-{gap['gap_number']}"
                for gap in payload["gaps"]
            }
        else:
            content = {"correct_alternative_ids": [payload["choices"][1]["alternative_id"]]}
        return StructuredLLMResponse(
            content=content, finish_reason="completed", usage=StructuredLLMUsage(total_tokens=17)
        )


def assert_item_local_suggestions(
    document: NativeExamDocument, suggestions: tuple[ExamWorkspaceAnswerKeySuggestionItem, ...]
) -> None:
    expected = [item for item in document.items if item.answer_key.origin.value == "absent"]
    assert [entry.item_id for entry in suggestions] == [item.item_id for item in expected]
    for item, entry in zip(expected, suggestions, strict=True):
        suggestion = entry.suggestion
        assert suggestion.fingerprint == answer_key_fingerprint(
            item, document.parent_of(item.item_id)
        )
        assert suggestion.provider_profile_id == "openai-gpt-6-luna-answer-key"
        if item.gaps:
            assert [gap.gap_id for gap in suggestion.gap_accepted_values] == [
                gap.gap_id for gap in item.gaps
            ]
            assert [gap.accepted_values for gap in suggestion.gap_accepted_values] == [
                (f"{item.item_id}-svar-{number}",) for number in range(1, len(item.gaps) + 1)
            ]
        else:
            assert suggestion.correct_choice_ids == (item.choices[1].choice_id,)
        # Merely receiving and keeping a suggestion is not teacher acceptance.
        data = item.model_dump()
        data["ai_suggestion"] = suggestion.model_dump()
        kept = type(item).model_validate(data)
        assert kept.answer_key == item.answer_key
        assert kept.review == item.review
        assert kept.review.state.value == "review_required"
        assert kept.answer_key.origin.value == "absent"
        assert all(not gap.accepted_values for gap in kept.gaps)


@pytest.mark.parametrize("source_key,zero_points", [(False, False), (True, False), (False, True)])
async def test_digiexam_worker_keeps_item_identity_and_review(source_key, zero_points):
    document = imported_document(uuid4(), source_key=source_key, zero_points=zero_points)
    before = document.model_dump(mode="json")
    model = CapturingModel()
    harness = WorkspaceHarness(provider=model, document=document)
    job = await harness.seed_claimed_job()
    finished = await harness.handler.handle(job=job)
    assert finished.status.value == "succeeded"
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert_item_local_suggestions(document, payload.suggestions)
    eligible = {item.item_id for item in document.items if item.answer_key.origin.value == "absent"}
    # Assert on captured prompts, not merely on the enqueue payload.
    assert {
        json.loads(request.user_payload)["item"]["item_id"] for request in model.requests
    } == eligible
    assert model.call_count == len(eligible)
    if source_key:
        assert "item_002" not in {request.item_id for request in model.requests}
        assert all("Indragen veckopeng" not in request.user_payload for request in model.requests)
    assert document.model_dump(mode="json") == before
