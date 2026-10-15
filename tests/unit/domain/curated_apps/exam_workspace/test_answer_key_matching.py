"""Matching answer-key suggestions on the recorded English matching items (D8)."""

import json

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_prompts import (
    MATCHING_ANSWER_KEY_SYSTEM_PROMPT,
    MATCHING_PROMPT_TEMPLATE_VERSION,
    plan_workspace_answer_key_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyItemProposal,
    AnswerKeyItemView,
    AnswerKeyViewKind,
    answer_key_item_views,
    proposal_from_model_content,
    suggestion_from_proposal,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    document_of,
    recorded_matching_items,
)

pytestmark = pytest.mark.unit


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


def _content(*pairs: tuple[int, int]) -> dict[str, JsonValue]:
    return {"pairs": [{"left_id": left, "right_id": right} for left, right in pairs]}


def _view(item: NativeExamItem) -> AnswerKeyItemView:
    return answer_key_item_views(document_of(item))[0]


def _suggestion(item: NativeExamItem, proposal: AnswerKeyItemProposal) -> NativeAnswerKeySuggestion:
    return suggestion_from_proposal(
        view=_view(item),
        proposal=proposal,
        provider_profile_id="p",
        model="m",
        prompt_template_version=MATCHING_PROMPT_TEMPLATE_VERSION,
    )


def test_unkeyed_recorded_matching_items_are_selected_with_native_order_lists() -> None:
    items = recorded_matching_items()
    assert len(items) == 3
    assert all(item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT for item in items)

    views = answer_key_item_views(document_of(*items))

    assert [view.item_id for view in views] == [item.item_id for item in items]
    for view, item in zip(views, items, strict=True):
        assert view.kind is AnswerKeyViewKind.MATCHING
        assert [text for _id, text in view.match_left] == [e.text for e in item.match_left]
        assert [text for _id, text in view.match_right] == [e.text for e in item.match_right]
        assert [i for i, _text in view.match_left] == [1, 2, 3]
        assert view.stem_text == "\n".join(item.plain_text_lines())


def test_keyed_recorded_matching_items_are_not_selected() -> None:
    assert answer_key_item_views(document_of(*recorded_matching_items(keyed=True))) == ()


def test_well_formed_proposal_is_kept_as_a_matching_suggestion() -> None:
    item = recorded_matching_items()[0]
    proposal = proposal_from_model_content(
        view=_view(item), content=_content((1, 2), (2, 3), (3, 1))
    )

    assert proposal is not None
    assert proposal.match_pairs == (
        ("left_001", "right_002"),
        ("left_002", "right_003"),
        ("left_003", "right_001"),
    )
    suggestion = _suggestion(item, proposal)
    kept = NativeExamItem.model_validate({**dict(item), "ai_suggestion": suggestion})

    assert kept.ai_suggestion is not None
    assert [(p.left_id, p.right_id) for p in kept.ai_suggestion.match_pairs] == [
        ("left_001", "right_002"),
        ("left_002", "right_003"),
        ("left_003", "right_001"),
    ]
    assert kept.answer_key.origin is NativeAnswerKeyOrigin.ABSENT


def test_proposal_may_leave_a_distractor_right_entry_unused() -> None:
    item = recorded_matching_items()[0]
    other_right = recorded_matching_items()[1].match_right[0].text
    widened = NativeExamItem.model_validate(
        {
            **dict(item),
            "match_right": (
                *item.match_right,
                NativeMatchRight(right_id="right_004", text=other_right),
            ),
        }
    )

    proposal = proposal_from_model_content(
        view=_view(widened), content=_content((1, 4), (2, 2), (3, 3))
    )

    assert proposal is not None
    assert _suggestion(widened, proposal).match_pairs[0].right_id == "right_004"


@pytest.mark.parametrize(
    ("label", "content"),
    [
        ("left entry unpaired", _content((1, 1), (2, 2))),
        ("left entry paired twice", _content((1, 1), (1, 2), (3, 3))),
        ("right entry used twice", _content((1, 1), (2, 1), (3, 3))),
        ("unknown left id", _content((1, 1), (2, 2), (9, 3))),
        ("unknown right id", _content((1, 1), (2, 2), (3, 9))),
        ("no pairs", _content()),
        ("pairs missing", {}),
        ("pairs not a list", {"pairs": "1-1"}),
        ("pair not an object", {"pairs": [[1, 1], [2, 2], [3, 3]]}),
        ("string ids", {"pairs": [{"left_id": "1", "right_id": "1"}] * 3}),
        ("boolean ids", {"pairs": [{"left_id": True, "right_id": True}] * 3}),
        ("missing right id", {"pairs": [{"left_id": 1}, {"left_id": 2}, {"left_id": 3}]}),
    ],
)
def test_malformed_matching_proposal_is_rejected(label: str, content: dict[str, JsonValue]) -> None:
    item = recorded_matching_items()[0]

    assert proposal_from_model_content(view=_view(item), content=content) is None, label


def test_matching_request_carries_both_lists_and_a_strict_pairs_schema() -> None:
    item = recorded_matching_items()[0]
    plan = plan_workspace_answer_key_candidates(
        job_id="job-1", views=(_view(item),), profile=_profile()
    )[0]
    request = plan.request

    assert request.prompt_template_version == MATCHING_PROMPT_TEMPLATE_VERSION
    assert request.system_prompt == MATCHING_ANSWER_KEY_SYSTEM_PROMPT
    payload = json.loads(request.user_payload)
    assert payload["left_entries"][0] == {"left_id": 1, "text": item.match_left[0].text}
    assert payload["right_entries"][2] == {"right_id": 3, "text": item.match_right[2].text}
    schema = request.output_spec.json_schema
    assert schema["required"] == ["pairs"]
    assert schema["additionalProperties"] is False


def test_suggestion_round_trips_pairs_through_json() -> None:
    item = recorded_matching_items()[0]
    proposal = proposal_from_model_content(
        view=_view(item), content=_content((1, 1), (2, 2), (3, 3))
    )
    assert proposal is not None
    suggestion = _suggestion(item, proposal)

    restored = NativeAnswerKeySuggestion.model_validate(suggestion.model_dump(mode="json"))

    assert restored == suggestion
    assert [(p.left_id, p.right_id) for p in restored.match_pairs] == [
        ("left_001", "right_001"),
        ("left_002", "right_002"),
        ("left_003", "right_003"),
    ]
