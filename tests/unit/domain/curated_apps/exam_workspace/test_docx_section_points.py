"""Equal split of printed section totals, checked against real corpus chunks."""

from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
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


def test_section_total_is_shared_equally_and_input_order_is_kept():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)
    assert len(accepted) == 20

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset())

    assert [anchors for _, anchors in result] == [anchors for _, anchors in accepted]
    assert _points(result) == [3, 3, 4, 4, 2] + [1] * 15
    assert [item for item, _ in result[:5]] == [item for item, _ in accepted[:5]]
    # The closing total line has no members of its own and is not reported; the
    # following section is reported because its members print their own points.
    assert unsplit == ()


def test_one_member_printing_points_leaves_the_whole_section_unsplit():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks, printing_member=7)

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset())

    assert result == accepted
    assert unsplit == (_anchor(6),)


def test_total_not_dividing_evenly_leaves_the_section_unsplit():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks, dropped_member=14)
    assert len(accepted) == 19

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset())

    assert result == accepted
    assert unsplit == (_anchor(6),)


def test_unbuilt_chunk_inside_the_section_leaves_it_unsplit():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset({_anchor(9)}))

    assert result == accepted
    assert unsplit == (_anchor(6),)


def test_unbuilt_chunk_outside_every_section_range_does_not_block_the_split():
    chunks = _chunks(_SECTIONED)
    accepted, instructions = _sectioned_inputs(chunks)

    result, unsplit = split_section_totals(
        chunks, accepted, instructions, frozenset({_anchor(3), "body:9999"})
    )

    assert _points(result) == [3, 3, 4, 4, 2] + [1] * 15
    assert unsplit == ()


def test_section_whose_members_all_print_points_is_unchanged_and_not_reported():
    chunks = _chunks(_ALL_PRINTED)
    accepted = tuple(
        _entry(chunks, (_anchor(start), _anchor(start + 1)), 1) for start in range(7, 55, 2)
    )
    assert len(accepted) == 24
    instructions = (_line(_anchor(3), None), _line(_anchor(5), 24))

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset())

    assert result == accepted
    assert unsplit == ()


def test_total_over_a_single_question_stays_unsplit():
    """A question's own trailing points line, misread as a section total, must not
    hand that question the whole section total."""
    chunks = _chunks("svenska_2_grammatik_omprov_variant_1_med_facit")
    accepted = (
        _entry(chunks, tuple(_anchor(n) for n in range(8, 13)), None),
        _entry(chunks, tuple(_anchor(n) for n in range(16, 22)), None),
        _entry(chunks, tuple(_anchor(n) for n in range(25, 30)), None),
    )
    instructions = (
        _line(_anchor(6), 12),
        _line(_anchor(13), 6),
        _line(_anchor(22), 2),
        _line(_anchor(30), 4),
        _line(_anchor(34), 8),
    )

    result, unsplit = split_section_totals(chunks, accepted, instructions, frozenset())

    assert result == accepted
    assert unsplit == (_anchor(6), _anchor(13), _anchor(22))
