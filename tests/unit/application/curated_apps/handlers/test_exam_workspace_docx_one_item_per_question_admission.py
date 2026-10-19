"""A grouped question is admitted as one item (TASK-SKRIPT-39-04-12 C3).

A reply that spreads one question's body over several entries, or puts two questions' bodies
in one entry, gets no converted item for those questions: each becomes its source review item.
"""

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    MERGED_QUESTIONS_REASON,
    SPLIT_QUESTION_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_one_item_test_support import (
    _OTHER,
    _QUESTION,
    _is_source_review,
    _item,
    _state,
    _texts,
)

pytestmark = pytest.mark.unit


def test_a_question_split_into_one_item_per_sentence_becomes_one_source_review_item():
    state = _state(_QUESTION)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    "Hunden skäller på brevbäraren.",
                    "1",
                ),
                _item(["body:0004"], "I morgon reser min syster till Malmö.", "2"),
            ]
        },
        state,
    )

    ((item, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert _is_source_review(item, SPLIT_QUESTION_REASON)
    assert anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert _texts(item) == [text for _, text in _QUESTION]
    # The question keeps the total it prints; no share of it goes to a sentence.
    assert item.points == 4
    assert state.result().document.items[0].points == 4
    assert [(e.code, e.anchors) for e in state.events if e.stage == "admission"] == [
        ("question_split", anchors)
    ]
    assert state.pending == ()


def test_a_split_question_leaves_its_neighbour_converted():
    state = _state(_QUESTION, _OTHER)

    admit_batch(
        {
            "items": [
                _item(["body:0001", "body:0002", "body:0003"], "Hunden skäller.", "1"),
                _item(["body:0004"], "I morgon reser min syster till Malmö.", "2"),
                _item(["body:0005"], "Förklara vad ett predikat är.", "Uppgift 1.2"),
            ]
        },
        state,
    )

    (split, split_anchors), (other, other_anchors) = [(a.item, h) for a, h in state.accepted]
    assert _is_source_review(split, SPLIT_QUESTION_REASON)
    assert split_anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert other.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert other_anchors == ("body:0005",)
    assert state.pending == ()


def test_two_questions_merged_into_one_item_each_become_their_own_source_review_item():
    state = _state(_QUESTION, _OTHER)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003", "body:0004", "body:0005"],
                    "Stryk under subjektet. Förklara vad ett predikat är.",
                    "1",
                )
            ]
        },
        state,
    )

    (first, first_anchors), (second, second_anchors) = [(a.item, h) for a, h in state.accepted]
    assert _is_source_review(first, MERGED_QUESTIONS_REASON)
    assert _is_source_review(second, MERGED_QUESTIONS_REASON)
    assert first_anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert second_anchors == ("body:0005",)
    assert _texts(second) == [_OTHER[0][1]]
    assert state.pending == ()


@pytest.mark.parametrize(
    "label",
    [("heading", "Uppgift 1.1: Subjekt (4 p)"), ("paragraph", "4 p")],
    ids=["question_heading", "points_line"],
)
def test_a_separately_emitted_heading_or_points_line_is_no_split(label: tuple[str, str]):
    # The heading or points line joins the entry that holds its question's body.
    body = (("paragraph", "Stryk under subjektet i varje mening."),)
    question = (label, *body) if label[0] == "heading" else (*body, label)
    state = _state(question)
    label_anchor, body_anchor = (
        ("body:0001", "body:0002") if label[0] == "heading" else ("body:0002", "body:0001")
    )

    admit_batch(
        {
            "items": [
                _item([label_anchor], label[1], "1"),
                _item([body_anchor], "Stryk under subjektet i varje mening.", "1"),
            ]
        },
        state,
    )

    ((item, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert set(anchors) == {"body:0001", "body:0002"}
    assert not [e for e in state.events if e.code in {"question_split", "questions_merged"}]
