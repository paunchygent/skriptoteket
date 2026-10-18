"""Printed points reach the built items in one pass: question points, then part shares (D2, D38)."""

from decimal import Decimal

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import printed_points_plan
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    ScoredItems,
    apply_printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    recorded_matching_items,
)

pytestmark = pytest.mark.unit


def _exam(*lines: str) -> tuple[tuple[DocxChunk, ...], tuple[tuple[str, ...], ...]]:
    """Chunks from source lines: "# " marks a heading and "Q " a question's opening line."""
    chunks: list[DocxChunk] = []
    questions: list[tuple[str, ...]] = []
    for number, line in enumerate(lines):
        anchor = f"body:{number:04d}"
        kind = "heading" if line.startswith("# ") else "paragraph"
        text = line.removeprefix("# ").removeprefix("Q ")
        chunks.append(DocxChunk(anchor, kind, text, text))
        if line.startswith("Q "):
            questions.append((anchor,))
    return tuple(chunks), tuple(questions)


def _items(
    chunks: tuple[DocxChunk, ...],
    questions: tuple[tuple[str, ...], ...],
    points: tuple[int | float | None, ...],
) -> tuple[NativeExamItem, ...]:
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    return tuple(
        review_chunk_item(by_anchor[own[0]], "test").model_copy(
            update={"item_id": f"item_{n:03d}", "sequence": n, "points": p}
        )
        for n, (own, p) in enumerate(zip(questions, points, strict=True), 1)
    )


def _score(
    chunks: tuple[DocxChunk, ...],
    questions: tuple[tuple[str, ...], ...],
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...] = (),
) -> ScoredItems:
    return apply_printed_points(
        items,
        parents,
        printed_points_plan(chunks, questions),
        {chunk.anchor: chunk for chunk in chunks},
    )


def _points(scored: ScoredItems) -> list[int | float | None]:
    return [item.points for item in scored.items]


def _marked(scored: ScoredItems) -> list[bool]:
    return [item.points_estimated for item in scored.items]


def _parent(parent_id: str, *item_ids: str) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        instruction=(
            NativeParagraph(
                segments=(NativeTextSegment(kind="text", text="Del", marks=()),), heading_level=None
            ),
        ),
        item_ids=item_ids,
    )


_DEL_1 = ("# Del 1: litteraturhistoria, 15 poäng", *(f"Q {n}. Fråga {n}" for n in range(1, 16)))


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
