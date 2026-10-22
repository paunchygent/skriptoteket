"""Golden-shape tests: workspace answer-key prompt payloads are asserted directly.

The workspace owns its payload builders in `exam_workspace/answer_key_prompts.py`
(they reuse the shared DigiExam system prompts, template versions, and output
specs). The requests must reuse the same system prompts, prompt-template
versions, and structured output specs.
"""

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    system_prompt_for_answer_key_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import DigiExamItemType
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_prompts import (
    choice_answer_key_model_payload_from_view,
    choice_decision_output_spec,
    gap_fill_answer_key_model_payload_from_view,
    numbered_gap_fill_output_spec,
    plan_workspace_answer_key_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint_for_view,
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body

pytestmark = pytest.mark.unit

# Pinned from the unchanged answer-key view: labels must never alter it.
_TWO_PAIR_FINGERPRINT = "56ac0be0fa7c0c2a631abfd11294a54d882589f97a1d0c503af4d0d023368c47"


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-6-luna-answer-key",
        model="gpt-6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.DETERMINISTIC,
    )


def _document(item: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _native_choice_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeTextSegment(text="Choose the Greek letter.", marks=()),),
            ),
        ),
        points=2,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Alpha")),
            NativeChoice(choice_id="choice_002", body=plain_body("Beta")),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=_review(),
    )


def _native_gap_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="The capital of Sweden is ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=".", marks=()),
                ),
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001"),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=_review(),
    )


class TestChoicePromptParity:
    def test_choice_payload_has_the_workspace_shape(self) -> None:
        view = answer_key_item_views(_document(_native_choice_item()))[0]
        workspace_payload = choice_answer_key_model_payload_from_view(view)

        assert workspace_payload == {
            "task": {
                "name": "select_teacher_intended_choice_answer_key",
                "item_type": "single_choice",
                "instruction": (
                    "Read the item as a teacher-authored exam question. This item type has "
                    "exactly one correct answer. Select the single teacher-intended correct "
                    "choice from the listed choices. Use only the provided choice_value values."
                ),
            },
            "item": {"item_id": "item_001", "stem": "Choose the Greek letter."},
            "choices": [
                {"choice_value": "1", "alternative_id": 1, "text": "Alpha"},
                {"choice_value": "2", "alternative_id": 2, "text": "Beta"},
            ],
            "selection_rules": {"min_choices": 1, "max_choices": 1},
            "output": {
                "provider_output_mode": "json_schema",
                "answer_shape": (
                    "Return a JSON object with a correct_alternative_ids array "
                    "containing exactly one integer id, using only the listed "
                    "alternative_id values."
                ),
            },
        }

    def test_choice_request_reuses_system_prompt_template_and_spec(self) -> None:
        view = answer_key_item_views(_document(_native_choice_item()))[0]
        plan = plan_workspace_answer_key_candidates(
            job_id="job-1", views=(view,), profile=_profile()
        )[0]

        assert plan.request.system_prompt == system_prompt_for_answer_key_item(
            DigiExamItemType.SINGLE_CHOICE
        )
        assert plan.request.prompt_template_version == CHOICE_PROMPT_TEMPLATE_VERSION
        assert plan.request.output_spec == choice_decision_output_spec()
        assert plan.request.item_type == DigiExamItemType.SINGLE_CHOICE.value


class TestGapFillPromptParity:
    def test_gap_payload_has_the_workspace_shape(self) -> None:
        view = answer_key_item_views(_document(_native_gap_item()))[0]
        workspace_payload = gap_fill_answer_key_model_payload_from_view(view)

        assert workspace_payload["task"] == {
            "name": "complete_teacher_intended_gap_fill_answer_key",
            "item_type": "gap_fill",
            "instruction": (
                "Read the cloze item as a teacher-authored exam question. "
                "Each [number] marker is one blank. Choose the "
                "teacher-intended accepted value for every numbered blank."
            ),
        }
        assert workspace_payload["item"] == {
            "item_id": "item_001",
            "cloze_text": "The capital of Sweden is [1].",
        }
        assert workspace_payload["gaps"] == [
            {"gap_number": 1, "label": "The capital of Sweden is"},
        ]
        output = workspace_payload["output"]
        assert isinstance(output, dict)
        assert output["provider_output_mode"] == "json_schema"
        assert output["json_shape"] == (
            'Return one JSON object. Use string keys "1" through "1" for the numbered blanks.'
        )
        assert "word bank" in str(output["accepted_values"])

    def test_gap_request_reuses_system_prompt_template_and_spec(self) -> None:
        view = answer_key_item_views(_document(_native_gap_item()))[0]
        plan = plan_workspace_answer_key_candidates(
            job_id="job-1", views=(view,), profile=_profile()
        )[0]

        assert plan.request.system_prompt == system_prompt_for_answer_key_item(
            DigiExamItemType.GAP_FILL
        )
        assert plan.request.prompt_template_version == GAP_FILL_PROMPT_TEMPLATE_VERSION
        assert plan.request.output_spec == numbered_gap_fill_output_spec(1)
        assert plan.request.max_output_tokens == _profile().max_output_tokens


def _native_two_pair_gap_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Kingdom of mushrooms: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text="    Domain of bacteria: ", marks=()),
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001"), NativeGap(gap_id="gap_002")),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=_review(),
    )


class TestGapFillLabels:
    def test_gap_entries_carry_the_text_printed_before_each_marker(self) -> None:
        view = answer_key_item_views(_document(_native_two_pair_gap_item()))[0]

        payload = gap_fill_answer_key_model_payload_from_view(view)

        assert payload["gaps"] == [
            {"gap_number": 1, "label": "Kingdom of mushrooms"},
            {"gap_number": 2, "label": "Domain of bacteria"},
        ]

    def test_labels_leave_the_view_cloze_text_and_fingerprint_unchanged(self) -> None:
        view = answer_key_item_views(_document(_native_two_pair_gap_item()))[0]
        before = view.model_dump()
        fingerprint = answer_key_fingerprint_for_view(view)

        payload = gap_fill_answer_key_model_payload_from_view(view)

        item = payload["item"]
        assert isinstance(item, dict)
        assert item["cloze_text"] == view.cloze_text
        assert view.cloze_text == "Kingdom of mushrooms: [1] Domain of bacteria: [2]"
        assert view.model_dump() == before
        assert answer_key_fingerprint_for_view(view) == fingerprint
        assert fingerprint == _TWO_PAIR_FINGERPRINT

    def test_gap_prompt_template_version_is_bumped_for_labels(self) -> None:
        assert GAP_FILL_PROMPT_TEMPLATE_VERSION == "digiexam_gap_fill_answer_key_prompt_v2"


def test_profile_rejects_output_budget_at_or_above_context_window() -> None:
    with pytest.raises(ValueError):
        StructuredLLMProviderProfile(
            provider_id="openai-gpt-6-luna-answer-key",
            model="gpt-6-luna",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=True,
            context_window_tokens=4_096,
            max_output_tokens=4_096,
        )


class TestOutputSpecShapes:
    def test_choice_spec_shape(self) -> None:
        spec = choice_decision_output_spec()

        assert spec.schema_name == "digiexam_choice_answer_key_decision_v1"
        assert spec.schema_version == "digiexam_choice_answer_key_decision_v1"
        assert spec.json_schema["required"] == ["correct_alternative_ids"]
        assert spec.json_schema["properties"] == {
            "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}}
        }

    def test_numbered_gap_fill_spec_shape(self) -> None:
        spec = numbered_gap_fill_output_spec(2)

        assert spec.schema_name == "digiexam_gap_fill_answer_key_decision_v1"
        assert spec.schema_version == "digiexam_gap_fill_answer_key_decision_v1"
        assert spec.json_schema["required"] == ["1", "2"]
        assert spec.json_schema["properties"] == {"1": {"type": "string"}, "2": {"type": "string"}}
        with pytest.raises(ValueError):
            numbered_gap_fill_output_spec(0)
