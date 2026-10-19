"""Printed question values are recorded as source points independently of scoring (F1)."""

from decimal import Decimal

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from tests.unit.domain.curated_apps.exam_workspace.docx_section_points_support import (
    _exam,
    _items,
    _marked,
    _points,
    _score,
    _source_points,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    recorded_matching_items,
)

pytestmark = pytest.mark.unit


def test_a_printed_question_value_is_recorded_as_source_points():
    chunks, questions = _exam("Q Fråga 1 om satsdelar och ordföljd (2 p)")

    scored = _score(chunks, questions, _items(chunks, questions, (9,)))

    assert _points(scored) == [2]
    assert _marked(scored) == [False]
    assert _source_points(scored) == [2]


def test_a_share_of_a_part_total_records_no_source_points():
    chunks, questions = _exam("# Del 1: 10 poäng", "Q 1.", "Q 2.")

    scored = _score(chunks, questions, _items(chunks, questions, (None, None)))

    assert _points(scored) == [5, 5]
    assert _marked(scored) == [True, True]
    assert _source_points(scored) == [None, None]


def test_single_unprinted_remainder_stores_null_source_points():
    chunks, questions = _exam(
        "# Del 1: 10 poäng", "Q 1.", "Poäng: 3 poäng", "Q 2.", "Poäng: 3 poäng", "Q 3."
    )

    scored = _score(chunks, questions, _items(chunks, questions, (3, 3, 9)))

    assert _points(scored) == [3, 3, 4]
    assert _marked(scored) == [False] * 3
    assert _source_points(scored) == [3, 3, None]


def test_multi_question_unprinted_share_stores_null_source_points():
    chunks, questions = _exam("# Del 1: 10 poäng", "Q 1.", "Q 2.", "Q 3.")

    scored = _score(chunks, questions, _items(chunks, questions, (None, None, None)))

    assert _points(scored) == [4, 3, 3]
    assert _marked(scored) == [True] * 3
    assert _source_points(scored) == [None, None, None]


def test_printed_value_survives_a_refused_rubric_change():
    chunks, questions = _exam("Q Fråga om satsdelar och ordföljd (1 p)")
    (item,) = _items(chunks, questions, (2,))
    rubric = item.model_copy(
        update={
            "source_points": 2,
            "criteria": (
                NativeExamCriterion(text="Ordklass.", points=1),
                NativeExamCriterion(text="Ordföljd.", points=1),
            ),
        }
    )

    scored = _score(chunks, questions, (rubric,))

    updated = scored.items[0]
    assert updated.points == 2
    assert updated.points_estimated is False
    assert updated.source_points == 1
    assert updated.review.state is NativeItemReviewState.REVIEW_REQUIRED


def test_fully_printed_questions_keep_their_printed_source_points():
    chunks, questions = _exam(
        "# Del 3: kortsvar, 5 poäng",
        "Q Fråga 21",
        "Poäng: 1 poäng",
        "Q Fråga 22",
        "Poäng: 2 poäng",
        "Q Fråga 23",
        "Poäng: 1 poäng",
        "Q Fråga 24",
        "Poäng: 1 poäng",
    )

    scored = _score(chunks, questions, _items(chunks, questions, (1, 2, 7, 1)))

    assert _points(scored) == [1, 2, 1, 1]
    assert _marked(scored) == [False] * 4
    assert _source_points(scored) == [1, 2, 1, 1]


def test_a_printed_matching_total_with_inexact_ticks_keeps_the_printed_source_points():
    chunks, questions = _exam("Q Matcha orden med deras definitioner nedan (10 p)")
    matching = recorded_matching_items(keyed=True)[0]
    assert len(matching.answer_key.match_pairs) == 3
    grid = matching.model_copy(update={"item_id": "item_001", "source_anchor": questions[0][0]})

    scored = _score(chunks, questions, (grid,))

    updated = scored.items[0]
    assert updated.points == 9.99
    assert updated.tick_points == Decimal("3.33")
    assert updated.points_estimated is True
    assert updated.source_points == 10
