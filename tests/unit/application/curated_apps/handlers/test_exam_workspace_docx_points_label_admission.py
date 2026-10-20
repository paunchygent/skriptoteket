"""A reply without points takes the one points label the item's own chunks print, and the
label leaves the stem (D3). Points the reply gives win over a printed label, and a points
paragraph the reply does not list still gives its question the points."""

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_left_out_test_support import (
    _item,
    _state,
    _stem_texts,
    _text,
)

pytestmark = pytest.mark.unit


def test_a_points_label_split_across_text_segments_leaves_the_stem():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)
    body: JsonValue = [{"segments": [_text("Vilket ord är ett substantiv? (1"), _text(" p)")]}]

    admit_batch({"items": [_item(["body:0001"], body=body, points=None)]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 1
    # D8: admission reads the points and leaves the reply body; the label leaves
    # at the final gate (D2), so the admitted stem keeps the wording.
    assert _stem_texts(admitted) == [stem]

    (final,) = state.result().document.items
    assert final.points == 1
    assert _stem_texts(final) == ["Vilket ord är ett substantiv?"]
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()


def test_a_choice_stem_ending_in_one_point_label_takes_the_point_and_loses_the_label():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem, "A. springa", "B. bord", "C. snabb")
    choices: list[JsonValue] = [
        {"text": "springa", "correct": False},
        {"text": "bord", "correct": True},
        {"text": "snabb", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003", "body:0004"],
                    kind="single_choice",
                    key_source="invented",
                    body=[{"segments": [_text(stem)]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 1
    assert _stem_texts(admitted) == [stem]
    assert admitted.review.reasons == ()

    (final,) = state.result().document.items
    assert final.points == 1
    assert _stem_texts(final) == ["Vilket ord är ett substantiv?"]
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()


@pytest.mark.parametrize(
    ("texts", "final_points", "final_stem"),
    [
        (
            ("Vilket ord är ett substantiv?", "A. bord", "B. springa"),
            None,
            "Vilket ord är ett substantiv?",
        ),
        (
            ("Vilket ord är ett substantiv? (1 p)", "A. bord (1 p)", "B. springa"),
            1,
            # D6+D3: the trailing label equals the settled points, so it leaves.
            "Vilket ord är ett substantiv?",
        ),
        (
            ("Vilket ord är ett substantiv? (0 p)", "A. bord", "B. springa"),
            None,
            "Vilket ord är ett substantiv? (0 p)",
        ),
    ],
    ids=["no-label", "two-labels", "zero-points"],
)
def test_a_reply_without_points_keeps_no_points_without_exactly_one_positive_label(
    texts, final_points, final_stem
):
    state = _state(*texts)
    choices: list[JsonValue] = [
        {"text": "bord", "correct": True},
        {"text": "springa", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    kind="single_choice",
                    key_source="invented",
                    body=[{"segments": [_text(texts[0])]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points is None
    assert _stem_texts(admitted) == [texts[0]]

    (final,) = state.result().document.items
    assert final.points == final_points
    assert _stem_texts(final) == [final_stem]
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()


def test_points_the_reply_gives_win_over_a_printed_label():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)

    admit_batch({"items": [_item(["body:0001"], body=[{"segments": [_text(stem)]}])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 2
    assert _stem_texts(admitted) == [stem]

    (final,) = state.result().document.items
    assert final.points == 1
    assert _stem_texts(final) == ["Vilket ord är ett substantiv?"]
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()


def test_a_points_paragraph_the_reply_does_not_list_still_gives_its_question_the_points():
    state = _state("Vilket ord är ett substantiv?", "A. bord", "B. springa", "(1 p)")
    choices: list[JsonValue] = [
        {"text": "bord", "correct": True},
        {"text": "springa", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    kind="single_choice",
                    key_source="invented",
                    body=[{"segments": [_text("Vilket ord är ett substantiv?")]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 1
    assert anchors[-1] == "body:0004"
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()

    (final,) = state.result().document.items
    assert final.points == 1
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()
