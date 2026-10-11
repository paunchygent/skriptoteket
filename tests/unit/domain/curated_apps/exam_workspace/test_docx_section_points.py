"""Split of printed section totals (D38), checked against real corpus chunks."""

from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    CHECK_POINTS_REASON,
    SectionPoints,
    split_section_totals,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItem
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

pytestmark = pytest.mark.unit

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
_SECTIONED = "svenska_2_kursavslutande_prov_med_facit"
_ALL_PRINTED = "bf26_english_1_unit_test_kap_1_2_med_facit"
_GRAMMAR = "svenska_2_grammatik_omprov_variant_1_med_facit"

Accepted = tuple[tuple[NativeExamItem, tuple[str, ...]], ...]


def _chunks(name: str) -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=(_CORPUS / f"{name}.docx").read_bytes())


def _anchor(number: int) -> str:
    return f"body:{number:04d}"


def _entry(
    chunks: tuple[DocxChunk, ...], anchors: tuple[str, ...], points: int | None
) -> tuple[NativeExamItem, tuple[str, ...]]:
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    assert all(anchor in by_anchor for anchor in anchors)
    item = review_chunk_item(by_anchor[anchors[0]], "test").model_copy(update={"points": points})
    return item, anchors


def _line(anchor: str, points: int | None) -> ProducedMetadata:
    return ProducedMetadata(text="line", source_anchors=(anchor,), points=points)


def _sectioned_inputs(
    chunks: tuple[DocxChunk, ...],
    *,
    printing_member: int | None = None,
    dropped_member: int | None = None,
) -> tuple[Accepted, tuple[ProducedMetadata, ...]]:
    unprinted = [
        _entry(
            chunks,
            (_anchor(start), _anchor(start + 1), _anchor(start + 2)),
            2 if member == printing_member else None,
        )
        for member, start in enumerate(range(10, 53, 3))
        if member != dropped_member
    ]
    printed = [
        _entry(chunks, (_anchor(start), _anchor(start + 1), _anchor(start + 2)), points)
        for start, points in ((61, 3), (67, 3), (73, 4), (79, 4), (85, 2))
    ]
    # Listed out of document order: the printed items come first.
    accepted = (*printed, *unprinted)
    instructions = (
        _line(_anchor(4), None),
        _line(_anchor(59), 16),
        _line(_anchor(6), 15),
        _line(_anchor(55), 15),
    )
    return accepted, instructions


def _points(accepted: Accepted) -> list[int | float | None]:
    return [item.points for item, _ in accepted]


def _marked(accepted: Accepted) -> list[bool]:
    return [CHECK_POINTS_REASON in item.review.reasons for item, _ in accepted]


def _split(
    chunks: tuple[DocxChunk, ...],
    accepted: Accepted,
    instructions: tuple[ProducedMetadata, ...],
    unbuilt: frozenset[str] = frozenset(),
) -> SectionPoints:
    return split_section_totals(chunks, accepted, instructions, unbuilt)


def test_section_total_is_shared_equally_and_each_share_carries_the_check_mark():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)
    assert len(accepted) == 20

    split = _split(chunks, accepted, instructions)

    assert [anchors for _, anchors in split.accepted] == [anchors for _, anchors in accepted]
    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15
    assert _marked(split.accepted) == [False] * 5 + [True] * 15
    assert [item for item, _ in split.accepted[:5]] == [item for item, _ in accepted[:5]]
    assert split.absorbed == frozenset()


def test_points_the_model_gave_a_member_whose_source_prints_none_become_the_share():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks, printing_member=7)

    split = _split(chunks, accepted, instructions)

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15


def test_unclaimed_points_line_after_the_last_question_is_absorbed_not_that_questions_points():
    """Replay of the recorded one-family run: the last question of the section took the
    section's closing points line as its own points without claiming it, and the line was
    left unbuilt."""
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks)
    last = len(accepted) - 1
    item, anchors = accepted[last]
    assert anchors == (_anchor(52), _anchor(53), _anchor(54))
    accepted = (*accepted[:last], (item.model_copy(update={"points": 15}), anchors))
    instructions = (_line(_anchor(4), 36), _line(_anchor(6), 15), _line(_anchor(59), 16))

    split = _split(chunks, accepted, instructions, frozenset({_anchor(55)}))

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15
    assert split.absorbed == frozenset({_anchor(55)})


def test_claimed_closing_points_line_does_not_make_the_last_question_print_points():
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks)
    last = len(accepted) - 1
    item, anchors = accepted[last]
    accepted = (
        *accepted[:last],
        (item.model_copy(update={"points": 15}), (*anchors, _anchor(55))),
    )
    instructions = (_line(_anchor(6), 15), _line(_anchor(59), 16))

    split = _split(chunks, accepted, instructions)

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15
    assert split.absorbed == frozenset()


def test_uneven_total_gives_earlier_questions_the_extra_point_in_document_order():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks, dropped_member=14)
    # Listed against document order, so the extra point must follow the source.
    accepted = (*accepted[:5], *reversed(accepted[5:]))
    assert len(accepted) == 19

    split = _split(chunks, accepted, instructions)

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 13 + [2]
    assert _marked(split.accepted) == [False] * 5 + [True] * 14


def test_ten_over_three_questions_gives_four_three_three():
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks)
    first_three = accepted[5:8]
    instructions = (_line(_anchor(6), 10), _line(_anchor(19), 5))

    split = _split(chunks, first_three, instructions)

    assert _points(split.accepted) == [4, 3, 3]
    assert _marked(split.accepted) == [True] * 3


def test_mixed_section_splits_what_remains_after_the_printed_points():
    """One total of 33 over both parts of the exam. Question 15's run reaches the first
    part's points line and the second part's heading, so its own 2 points stay beside the
    printed 16, and 15 remain for questions 1-14."""
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks, printing_member=14)

    split = _split(chunks, accepted, (_line(_anchor(6), 33),))

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [2] + [1] * 13 + [2]
    assert _marked(split.accepted) == [False] * 5 + [True] * 14 + [False]


def test_question_left_without_a_whole_point_keeps_the_models_reading():
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks, printing_member=13)
    accepted = (*accepted[:19], (accepted[19][0].model_copy(update={"points": 2}), accepted[19][1]))

    split = _split(chunks, accepted, (_line(_anchor(6), 30),))

    # 30 less the printed 18 leaves 12 for 14 questions: the last two keep the model's
    # reading, none for question 13 and 2 for question 14.
    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 12 + [None, 2] + [2]
    assert _marked(split.accepted) == [False] * 5 + [True] * 14 + [False]


def test_when_nothing_remains_the_models_reading_stands_and_is_marked():
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks, printing_member=3)

    split = _split(chunks, accepted, (_line(_anchor(6), 16),))

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [None] * 3 + [2] + [None] * 11
    assert _marked(split.accepted) == [False] * 5 + [True] * 14 + [False]


def test_unbuilt_chunk_inside_the_section_does_not_withhold_the_split():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)

    split = _split(chunks, accepted, instructions, frozenset({_anchor(9)}))

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15
    assert _marked(split.accepted) == [False] * 5 + [True] * 15
    assert split.absorbed == frozenset()


def test_unbuilt_chunk_outside_every_section_range_does_not_block_the_split():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)

    split = _split(chunks, accepted, instructions, frozenset({_anchor(3), "body:9999"}))

    assert _points(split.accepted) == [3, 3, 4, 4, 2] + [1] * 15


def test_member_whose_own_points_line_went_unclaimed_keeps_its_points():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)
    printed = [(item, anchors[:2]) for item, anchors in accepted[:5]]
    accepted = (*printed, *accepted[5:])

    split = _split(chunks, accepted, instructions)

    assert _points(split.accepted)[:5] == [3, 3, 4, 4, 2]
    assert _marked(split.accepted)[:5] == [False] * 5


def test_section_whose_members_all_print_points_is_unchanged_and_not_reported():
    chunks = _chunks(_ALL_PRINTED)
    accepted = tuple(
        _entry(chunks, (_anchor(start), _anchor(start + 1)), 1) for start in range(7, 55, 2)
    )
    assert len(accepted) == 24
    instructions = (_line(_anchor(3), None), _line(_anchor(5), 24))

    split = _split(chunks, accepted, instructions)

    assert split.accepted == accepted


def test_single_question_section_keeps_the_points_line_after_it_as_its_own():
    """The last section of the grammar exam prints its total on the heading and the same
    number on the one question's own points line, which is no section points line."""
    chunks = _chunks(_GRAMMAR)
    claimed = _entry(chunks, tuple(_anchor(n) for n in range(85, 95)), 8)
    unclaimed = _entry(chunks, tuple(_anchor(n) for n in range(85, 94)), 8)
    instructions = (_line(_anchor(74), 8),)

    for accepted in ((claimed,), (unclaimed,)):
        split = _split(chunks, accepted, instructions, frozenset({_anchor(94)}))

        assert split.accepted == accepted
        assert split.absorbed == frozenset()


def test_single_question_that_prints_no_points_gets_the_whole_total_marked():
    chunks = _chunks(_SECTIONED)
    accepted, _ = _sectioned_inputs(chunks)
    instructions = (_line(_anchor(6), 15), _line(_anchor(13), 16))

    split = _split(chunks, accepted[5:6], instructions)

    assert _points(split.accepted) == [15]
    assert _marked(split.accepted) == [True]


def test_points_lines_reported_as_instructions_start_no_section():
    """A question's own trailing points line misread as a section total closes the
    questions before it, so each question keeps its printed points unmarked."""
    chunks = _chunks(_GRAMMAR)
    accepted = (
        _entry(chunks, tuple(_anchor(n) for n in range(8, 13)), 6),
        _entry(chunks, tuple(_anchor(n) for n in range(16, 22)), 2),
        _entry(chunks, tuple(_anchor(n) for n in range(25, 30)), 4),
    )
    instructions = (
        _line(_anchor(6), 12),
        _line(_anchor(13), 6),
        _line(_anchor(22), 2),
        _line(_anchor(30), 4),
        _line(_anchor(34), 8),
    )

    split = _split(chunks, accepted, instructions)

    assert split.accepted == accepted
