"""Answer-key completion reads a grouped question under its parent's instruction (D10).

Each recorded corpus exam is replayed; a real child of a parent loses its key, as a teacher's
cleared key does, and the actual payload the model receives must still show the shared
instruction, such as the word bank the child's answers come from.
"""

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    numbered_gap_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_prompts import (
    choice_answer_key_model_payload_from_view,
    gap_fill_answer_key_model_payload_from_view,
    matching_answer_key_model_payload_from_view,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyItemView,
    AnswerKeyViewKind,
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItemKind,
    NativeGapSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.scripts.exam_conversion_corpus_support import RECORDED_STEMS, replayed

pytestmark = pytest.mark.unit

_KEYED = (
    NativeExamItemKind.GAP_FILL,
    NativeExamItemKind.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE,
    NativeExamItemKind.MATCHING,
)


def _without_key(document: NativeExamDocument, item_id: str) -> NativeExamDocument:
    data = document.model_dump(mode="json")
    child = next(item for item in data["items"] if item["item_id"] == item_id)
    child["answer_key"] = {"origin": "absent"}
    if child["kind"] == "matching":
        child["points"] = None
        child["points_estimated"] = False
    for gap in child["gaps"]:
        gap["accepted_values"] = []
    return NativeExamDocument.model_validate(data)


def _payload(view: AnswerKeyItemView) -> dict[str, JsonValue]:
    if view.kind is AnswerKeyViewKind.GAP_FILL:
        return gap_fill_answer_key_model_payload_from_view(view)
    if view.kind is AnswerKeyViewKind.MATCHING:
        return matching_answer_key_model_payload_from_view(view)
    return choice_answer_key_model_payload_from_view(view)


def _payload_item(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    item = payload["item"]
    assert isinstance(item, dict)
    return item


@pytest.mark.parametrize("stem", RECORDED_STEMS)
def test_cleared_corpus_items_keep_parent_context_and_response_data(stem: str) -> None:
    document, _ = replayed(stem)
    before = document.model_dump()
    children = [item for item in document.items if item.kind in _KEYED]
    assert children
    for child in children:
        parent = document.parent_of(child.item_id)
        unkeyed = _without_key(document, child.item_id)
        cleared = next(item for item in unkeyed.items if item.item_id == child.item_id)
        assert (cleared.body, cleared.choices, cleared.match_left, cleared.match_right) == (
            child.body,
            child.choices,
            child.match_left,
            child.match_right,
        )
        (view,) = [v for v in answer_key_item_views(unkeyed) if v.item_id == child.item_id]
        payload = _payload(view)
        item = _payload_item(payload)
        if parent is not None:
            assert item["instruction"] == body_plain_text(parent.instruction), (stem, child.item_id)
        else:
            assert "instruction" not in item
        assert item["item_id"] == child.item_id
        assert "title" not in item
        assert view.stem_text == "\n".join(child.plain_text_lines())
        if view.kind is AnswerKeyViewKind.GAP_FILL:
            assert view.gap_ids == tuple(
                segment.gap_id
                for paragraph in child.body
                for segment in paragraph.segments
                if isinstance(segment, NativeGapSegment)
            )
            assert tuple(gap.gap_id for gap in cleared.gaps) == tuple(
                gap.gap_id for gap in child.gaps
            )
            assert payload["gaps"] == [
                {"gap_number": number, "label": label}
                for number, label in enumerate(
                    numbered_gap_labels(view.cloze_text, len(child.gaps)), start=1
                )
            ]
        elif view.kind is AnswerKeyViewKind.MATCHING:
            assert payload["left_entries"] == [
                {"left_id": int(entry.left_id.removeprefix("left_")), "text": entry.text}
                for entry in child.match_left
            ]
            assert payload["right_entries"] == [
                {"right_id": int(entry.right_id.removeprefix("right_")), "text": entry.text}
                for entry in child.match_right
            ]
        else:
            assert payload["choices"] == [
                {
                    "choice_value": str(int(choice.choice_id.removeprefix("choice_"))),
                    "alternative_id": int(choice.choice_id.removeprefix("choice_")),
                    "text": choice.text,
                }
                for choice in child.choices
            ]
        shown = item.get("cloze_text") or item.get("stem")
        assert isinstance(shown, str)
        if view.kind is not AnswerKeyViewKind.GAP_FILL:
            assert shown == "\n".join(child.plain_text_lines())
    assert document.model_dump() == before


def test_word_bank_child_payload_keeps_bank_directions_and_numbered_body() -> None:
    document, _ = replayed("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    (view,) = [
        view
        for view in answer_key_item_views(_without_key(document, "item_046"))
        if view.item_id == "item_046"
    ]
    payload = _payload(view)
    item = _payload_item(payload)
    parent = document.parent_of("item_046")
    assert parent is not None
    assert item["instruction"] == body_plain_text(parent.instruction)
    assert "Choose a word to fill the gaps. Three of the words will not be used." in (
        view.instruction
    )
    assert "depict | herbal | persecution | target" in view.instruction
    assert "fatal | infant | rewarding" in view.instruction
    assert item["cloze_text"] == "My aunt is a great believer in Chinese [1] medicines."
    assert view.gap_ids == ("gap_001",)
    assert payload["gaps"] == [{"gap_number": 1, "label": "My aunt is a great believer in Chinese"}]


def test_a_standalone_question_payload_has_no_instruction() -> None:
    document, _ = replayed(RECORDED_STEMS[0])
    standalone = next(
        item
        for item in document.items
        if item.kind in _KEYED and document.parent_of(item.item_id) is None
    )
    (view,) = [
        v
        for v in answer_key_item_views(_without_key(document, standalone.item_id))
        if v.item_id == standalone.item_id
    ]
    assert "instruction" not in _payload_item(_payload(view))
