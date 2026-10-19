"""Printed points reach the built items in one pass: question points, then part shares (D2, D38)."""

from decimal import Decimal

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from tests.unit.domain.curated_apps.exam_workspace.docx_section_points_support import (
    _DEL_1,
    _exam,
    _items,
    _marked,
    _parent,
    _points,
    _score,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    recorded_matching_items,
)

pytestmark = pytest.mark.unit


def test_a_part_total_is_shared_equally_over_its_unprinted_questions_and_marked():
    chunks, questions = _exam(*_DEL_1, "Poäng: 15 poäng")

    scored = _score(chunks, questions, _items(chunks, questions, (None,) * 15))

    assert _points(scored) == [1] * 15
    assert _marked(scored) == [True] * 15


@pytest.mark.parametrize("reply", [None, 1, 15, 7])
def test_the_closing_line_is_the_parts_whatever_the_last_question_replied(reply):
    """Del 1's closing "Poäng: 15 poäng" restates the part's total: it is never q15's own."""
    chunks, questions = _exam(*_DEL_1, "Poäng: 15 poäng", "# Del 2: grammatik, 3 poäng")
    replies = (None,) * 14 + (reply,)

    scored = _score(chunks, questions, _items(chunks, questions, replies))

    assert _points(scored) == [1] * 15
    assert _marked(scored) == [True] * 15


def test_the_closing_line_is_the_parts_even_when_the_question_holds_it():
    chunks, questions = _exam(*_DEL_1, "Poäng: 15 poäng")
    held = (*questions[:14], (*questions[14], chunks[-1].anchor))

    scored = _score(chunks, held, _items(chunks, held, (None,) * 14 + (15,)))

    assert _points(scored) == [1] * 15


def test_a_last_question_line_with_another_value_is_that_questions_own():
    chunks, questions = _exam(
        "# Del 2: grammatik, 16 poäng",
        "Q Fråga 16",
        "Poäng: 3 poäng",
        "Q Fråga 17",
        "Poäng: 3 poäng",
        "Q Fråga 18",
        "Poäng: 4 poäng",
        "Q Fråga 19",
        "Poäng: 4 poäng",
        "Q Fråga 20",
        "Poäng: 2 poäng",
        "# Del 3: kortsvar, 5 poäng",
    )

    scored = _score(chunks, questions, _items(chunks, questions, (9, 9, 9, 9, 9)))

    assert _points(scored) == [3, 3, 4, 4, 2]
    assert _marked(scored) == [False] * 5


def test_printed_question_points_beat_the_reply_before_the_part_shares_what_remains():
    """F1: the part prints 10, q1 prints 2 and the reply says 8; q2 prints none."""
    chunks, questions = _exam("# Del 1: 10 poäng", "Q 1. Fråga", "Poäng: 2 poäng", "Q 2. Fråga")

    for reply in (2, 8):
        scored = _score(chunks, questions, _items(chunks, questions, (reply, None)))

        assert _points(scored) == [2, 8]
        assert _marked(scored) == [False, False]


def test_a_question_label_before_the_part_line_scores_the_first_question():
    """R3-1: the labelled line heads q1 across the part line; q2 takes the remainder."""
    chunks, questions = _exam("Poäng: 2 poäng", "# Del 1: 10 poäng", "Q 1. Fråga", "Q 2. Fråga")

    scored = _score(chunks, questions, _items(chunks, questions, (None, None)))

    assert _points(scored) == [2, 8]
    assert _marked(scored) == [False, False]


def test_a_same_total_line_after_the_next_part_line_scores_the_last_question():
    """Review-4: a part's closer lies inside its part; after the next part line it is q2's."""
    chunks, questions = _exam(
        "# Del 1: 2 poäng", "Q 1. Fråga", "Q 2. Fråga", "# Del 2: 7 poäng", "Poäng: 2 poäng"
    )

    scored = _score(chunks, questions, _items(chunks, questions, (None, None)))

    assert _points(scored) == [None, 2]
    assert _marked(scored) == [False, False]


@pytest.mark.parametrize(
    ("closing", "expected"),
    [("/4 p", [4, 8]), ("/5 p", [7, 8])],
    ids=["same-value-pair", "differing-pair"],
)
def test_a_questions_lines_print_their_one_distinct_value(
    closing: str, expected: list[int]
) -> None:
    """The omprov heading "(4 p)" and its "/4 p" line print 4; a differing pair prints none."""
    chunks, questions = _exam(
        "Q Uppgift 1.1: Morfemanalys (4 p)",
        "Dela upp följande ord i morfem.",
        closing,
        "Q Uppgift 1.2: Identifiera fraser i texten (8 p)",
        "/8 p",
    )

    scored = _score(chunks, questions, _items(chunks, questions, (7, 2)))

    assert _points(scored) == expected
    assert _marked(scored) == [False, False]


def test_a_printed_point_beats_a_reply_of_seven():
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


def test_an_uneven_total_gives_earlier_questions_the_extra_point_in_document_order():
    chunks, questions = _exam("# Del 1: 10 poäng", "Q 1.", "Q 2.", "Q 3.")
    items = _items(chunks, questions, (None, None, None))

    scored = _score(chunks, questions, tuple(reversed(items)))

    by_anchor = {item.source_anchor: item.points for item in scored.items}
    assert [by_anchor[own[0]] for own in questions] == [4, 3, 3]
    assert _marked(scored) == [True] * 3


def test_criteria_keep_their_points_while_two_or_more_questions_share_the_rest():
    chunks, questions = _exam("# Del 1: 8 poäng", "Q 1.", "Q 2.", "Q 3.")
    items = _items(chunks, questions, (None, None, None))
    rubric = items[0].model_copy(
        update={"points": 4, "criteria": (NativeExamCriterion(text="Resonemang.", points=4),)}
    )

    scored = _score(chunks, questions, (rubric, *items[1:]))

    assert scored.items[0] == rubric
    assert _points(scored) == [4, 2, 2]
    assert _marked(scored) == [False, True, True]


def test_one_unprinted_question_takes_the_exact_remainder_unmarked():
    chunks, questions = _exam(
        "# Del 1: 10 poäng", "Q 1.", "Poäng: 3 poäng", "Q 2.", "Poäng: 3 poäng", "Q 3."
    )

    scored = _score(chunks, questions, _items(chunks, questions, (3, 3, 9)))

    assert _points(scored) == [3, 3, 4]
    assert _marked(scored) == [False] * 3


def test_a_one_question_part_gives_it_the_whole_total_whether_or_not_it_restates_it():
    for lines in (
        ("# Del 4: 8 poäng", "Q Fråga 8."),
        ("# Del 4: 8 poäng", "Q Fråga 8.", "Poäng: 8 poäng"),
    ):
        chunks, questions = _exam(*lines)

        scored = _score(chunks, questions, _items(chunks, questions, (5,)))

        assert _points(scored) == [8]
        assert _marked(scored) == [False]


def test_when_nothing_remains_the_models_reading_stands_unmarked():
    chunks, questions = _exam("# Del 1: 4 poäng", "Q 1.", "Poäng: 4 poäng", "Q 2.", "Q 3.")

    scored = _score(chunks, questions, _items(chunks, questions, (4, None, 2)))

    assert _points(scored) == [4, None, 2]
    assert _marked(scored) == [False] * 3


def test_a_question_left_without_a_whole_point_keeps_the_models_reading():
    chunks, questions = _exam("# Del 1: 3 poäng", "Q 1.", "Poäng: 2 poäng", "Q 2.", "Q 3.")

    scored = _score(chunks, questions, _items(chunks, questions, (2, None, 5)))

    assert _points(scored) == [2, 1, 5]
    assert _marked(scored) == [False, True, False]


@pytest.mark.parametrize(("total", "tick_points", "points"), [(10, "1.66", 4.98), (6, "1", 3)])
def test_a_share_updates_a_grids_tick_value_and_total_together(total, tick_points, points):
    chunks, questions = _exam(f"# Del 1: {total} poäng", "Q 1.", "Q 2.")
    matching = recorded_matching_items(keyed=True)[0]
    assert len(matching.answer_key.match_pairs) == 3
    grid = matching.model_copy(update={"item_id": "item_001", "source_anchor": questions[0][0]})
    items = (grid, _items(chunks, questions, (None, None))[1])

    scored = _score(chunks, questions, items)

    updated = scored.items[0]
    assert updated.tick_points == Decimal(tick_points)
    assert updated.points == points
    assert updated.points_estimated is True
    assert NativeExamItem.model_validate(dict(updated)) == updated


def test_an_unkeyed_grid_keeps_no_total_until_ticks_can_determine_it():
    chunks, questions = _exam("# Del 1: 10 poäng", "Q 1.", "Q 2.")
    matching = recorded_matching_items()[0]
    grid = matching.model_copy(update={"item_id": "item_001", "source_anchor": questions[0][0]})

    scored = _score(chunks, questions, (grid, _items(chunks, questions, (None, None))[1]))

    assert scored.items[0] == grid
    assert scored.items[1].points == 5


def test_the_part_total_checks_only_a_parent_over_the_whole_part():
    """R3-3: a parent over part of a part's questions keeps its own total."""
    chunks, questions = _exam(
        "# Del 1: 10 poäng",
        "Q 1.",
        "Poäng: 2 poäng",
        "Q 2.",
        "Poäng: 3 poäng",
        "Q 3.",
        "Poäng: 5 poäng",
        "# Del 2: 4 poäng",
        "Q 4.",
        "Q 5.",
    )
    items = _items(chunks, questions, (2, 3, 5, 2, 2))
    parents = (
        _parent("parent_001", "item_001", "item_002"),
        _parent("parent_002", "item_004", "item_005"),
    )

    scored = _score(chunks, questions, items, parents)

    assert [parent.printed_total for parent in scored.parents] == [None, 4]


def test_questions_outside_every_part_keep_the_models_reading():
    chunks, questions = _exam("Total: 30 poäng", "Q 1.", "Q 2.")

    scored = _score(chunks, questions, _items(chunks, questions, (None, 4)))

    assert _points(scored) == [None, 4]
    assert _marked(scored) == [False, False]


def test_an_outer_part_never_shares_its_total_over_questions_that_print_their_own():
    # "Del 1 (20 p)" holds q1, which prints "/18 p", and q2 under its inner part heading
    # "(3 p)". The outer total is shared only over questions with neither, so q2 is never
    # first given the 2 points its three-criterion rubric cannot carry in whole points.
    chunks, questions = _exam(
        "# Del 1: Grammatik (20 p)",
        "Q Analysera meningen.",
        "/18 p",
        "# Uppgift 1.2: Ordklasser (3 p)",
        "Q Ange ordklass för de tre orden.",
    )
    items = _items(chunks, questions, (None, 3))
    rubric = items[1].model_copy(
        update={
            "criteria": tuple(NativeExamCriterion(text=f"Ord {n}.", points=1) for n in range(1, 4)),
            "review": items[1].review.model_copy(
                update={"state": NativeItemReviewState.REVIEW_COMPLETE, "reasons": ()}
            ),
        }
    )

    scored = _score(chunks, questions, (items[0], rubric))

    assert _points(scored) == [18, 3]
    assert _marked(scored) == [False, False]
    assert scored.items[1].review == rubric.review
    assert scored.items[1].criteria == rubric.criteria


def test_a_one_question_part_total_reaches_the_item_that_opens_with_its_part_heading():
    # Chapter_4 shape: part lines that repeat one identity head their one question each, so
    # the item starts at its part heading, an anchor no question holds. The part's printed
    # total still reaches that item. (A part line naming its own part opens a parent instead,
    # user ruling 2026-10-18.)
    chunks, questions = _exam(
        "# Part 3, Question 1 (2 p)",
        "Q Förklara vad som kännetecknar ett substantiv.",
        "# Part 3, Question 2 (3 p)",
        "Q Förklara vad som kännetecknar ett verb.",
    )
    noun, verb = _items(chunks, questions, (2, 5))
    opened = verb.model_copy(update={"source_anchor": "body:0002"})

    scored = _score(chunks, questions, (noun, opened))

    assert _points(scored) == [2, 3]
    assert _marked(scored) == [False, False]


def test_a_part_heading_review_item_never_takes_its_questions_total():
    # The part heading stayed unclaimed and became its own review item, ahead of the
    # question's item, which starts at the question's own chunk: the total reaches the latter.
    chunks, questions = _exam(
        "# Del 1: Substantiv (2 p)",
        "Q Förklara vad som kännetecknar ett substantiv.",
    )
    heading = review_chunk_item(chunks[0], "test").model_copy(
        update={"item_id": "item_000", "sequence": 0, "points": None}
    )
    (noun,) = _items(chunks, questions, (5,))

    scored = _score(chunks, questions, (heading, noun))

    assert _points(scored) == [None, 2]


def test_a_heading_part_opener_total_reaches_only_the_item_holding_it():
    # D12 read-label correction: the reader's number goes only to the one item
    # holding the read heading chunk; every other member gets None.
    chunks, questions = _exam("# Tempus (3 p)", "Q Förklara tempus 1.", "Q Förklara tempus 2.")
    held = ((chunks[0].anchor, *questions[0]), questions[1])

    scored = _score(chunks, held, _items(chunks, held, (None, None)))

    assert _points(scored) == [2, 1]
    assert list(scored.read_heading_points) == [3, None]


def test_a_plain_paragraph_part_opener_gives_no_read_number():
    # A part opener that is no heading carries no heading label.
    chunks, questions = _exam("Del 1: 6 poäng", "Q Fråga 1.", "Q Fråga 2.")

    scored = _score(chunks, questions, _items(chunks, questions, (None, None)))

    assert _points(scored) == [3, 3]
    assert list(scored.read_heading_points) == [None, None]


def test_a_question_owned_heading_line_carries_the_reader_s_number():
    # R8: the reader consumed the question-owned heading "Poäng: (3 p)", so
    # its item gets the read number; a plain paragraph line carries none.
    chunks, questions = _exam("# Poäng: (3 p)", "Q Förklara tempus.")

    scored = _score(chunks, questions, _items(chunks, questions, (None,)))

    assert list(scored.read_heading_points) == [3]


def test_a_question_owned_plain_line_carries_no_read_number():
    # The same points line as a plain paragraph is no read heading.
    chunks, questions = _exam("Poäng: 3 poäng", "Q Förklara tempus.")

    scored = _score(chunks, questions, _items(chunks, questions, (None,)))

    assert _points(scored) == [3]
    assert list(scored.read_heading_points) == [None]
