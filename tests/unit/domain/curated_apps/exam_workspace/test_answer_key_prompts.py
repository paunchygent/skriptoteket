"""Golden-shape tests: workspace prompts reuse the DigiExam answer-key line.

The workspace prompt payloads must stay shape-identical to the DigiExam
payloads (same task, instructions, selection rules, output text), and the
requests must reuse the same system prompts, prompt-template versions, and
structured output specs. An equivalent item is parsed from DXE bytes so any
drift in the shared prompt line fails here.
"""

import json
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.digiexam_source_parsing import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    choice_answer_key_model_payload,
    gap_fill_answer_key_model_payload,
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
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
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


def _dxe_upload(questions: list[dict[str, JsonValue]]) -> ConversionHubUpload:
    return ConversionHubUpload(
        filename="exam.dxe",
        content_type="application/octet-stream",
        file_bytes=json.dumps({"exams": [{"questions": questions}]}).encode("utf-8"),
    )


def _dxe_choice_item():
    upload = _dxe_upload(
        [
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
    )
    return parse_source_exam(upload=upload).items[0]


def _dxe_gap_item():
    upload = _dxe_upload(
        [
            {
                "id": 1,
                "title": "Gap without key",
                "about": "",
                "bodyHTML": ('<p>The capital of Sweden is <span dx-wg-id="gap-1">?</span>.</p>'),
                "images": [],
                "maxScore": 2,
                "type": 3,
                "blanks": [{"guid": "gap-1", "validations": []}],
            }
        ]
    )
    return parse_source_exam(upload=upload).items[0]


class TestChoicePromptParity:
    def test_choice_payload_matches_digiexam_shape(self) -> None:
        dxe_payload = choice_answer_key_model_payload(_dxe_choice_item())
        view = answer_key_item_views(_document(_native_choice_item()))[0]
        workspace_payload = choice_answer_key_model_payload_from_view(view)

        assert workspace_payload.keys() == dxe_payload.keys()
        assert workspace_payload["task"] == dxe_payload["task"]
        assert workspace_payload["selection_rules"] == dxe_payload["selection_rules"]
        assert workspace_payload["output"] == dxe_payload["output"]
        assert workspace_payload["choices"] == dxe_payload["choices"]
        workspace_item = workspace_payload["item"]
        dxe_item = dxe_payload["item"]
        assert isinstance(workspace_item, dict)
        assert isinstance(dxe_item, dict)
        assert "title" not in workspace_item
        assert dxe_item["title"] == "Single without key"
        assert workspace_item["stem"] == dxe_item["stem"]

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
    def test_gap_payload_matches_digiexam_shape(self) -> None:
        dxe_payload = gap_fill_answer_key_model_payload(_dxe_gap_item())
        view = answer_key_item_views(_document(_native_gap_item()))[0]
        workspace_payload = gap_fill_answer_key_model_payload_from_view(view)

        assert workspace_payload.keys() == dxe_payload.keys()
        assert workspace_payload["task"] == dxe_payload["task"]
        assert workspace_payload["gaps"] == dxe_payload["gaps"]
        assert workspace_payload["output"] == dxe_payload["output"]
        workspace_item = workspace_payload["item"]
        dxe_item = dxe_payload["item"]
        assert isinstance(workspace_item, dict)
        assert isinstance(dxe_item, dict)
        assert "title" not in workspace_item
        assert dxe_item["title"] == "Gap without key"
        assert workspace_item["cloze_text"] == dxe_item["cloze_text"]

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
            provider_id="openai-gpt-5.6-luna",
            model="gpt-5.6-luna",
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
