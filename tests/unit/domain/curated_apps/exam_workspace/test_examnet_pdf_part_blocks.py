"""PDF export: a part with no questions prints its instruction at its own place (G5, R2).

A childless part between two questions prints one ``part-instruction`` section between the
two item sections; an empty one prints nothing; a part with children keeps today's single
``parent-instruction`` before its first child only.
"""

import re
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
)

_PART_TEXT = "Delinstruktion: arbeta i par."
_ITEM_SECTION = '<section class="exam-item">'
_PART_SECTION = '<section class="part-instruction">'
_PARENT_DIV = '<div class="parent-instruction">'


def _question(sequence: int) -> NativeExamItem:
    return make_free_text_item(sequence=sequence, item_id=f"item_{sequence:03d}")


def _part(
    *,
    place: int,
    instruction: str | None = None,
    children: tuple[str, ...] = (),
) -> NativeExamParent:
    paragraphs = () if instruction is None else (make_paragraph(instruction),)
    return NativeExamParent(
        parent_id="parent_001",
        place=place,
        instruction=paragraphs,
        item_ids=children,
    )


def _document(
    items: list[NativeExamItem], parents: tuple[NativeExamParent, ...]
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Delprov",
        items=tuple(items),
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _section_positions(html: str) -> list[int]:
    return [match.start() for match in re.finditer(re.escape(_ITEM_SECTION), html)]


def test_a_childless_part_prints_its_instruction_between_the_questions() -> None:
    document = _document(
        [_question(1), _question(2)],
        (_part(place=1, instruction=_PART_TEXT),),
    )

    result = native_exam_to_pdf_document(document)

    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert result.html.count(_PART_SECTION) == 1
    assert result.html.count(_PART_TEXT) == 1
    first_item, _second_item = _section_positions(result.html)
    part_at = result.html.index(_PART_SECTION)
    assert first_item < part_at < result.html.index(_ITEM_SECTION, first_item + 1)
    assert part_at < result.html.index(_PART_TEXT)


def test_a_childless_part_with_an_empty_instruction_prints_nothing() -> None:
    document = _document(
        [_question(1), _question(2)],
        (_part(place=1),),
    )

    result = native_exam_to_pdf_document(document)

    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert result.html.count(_PART_SECTION) == 0
    assert len(_section_positions(result.html)) == 2


def test_a_part_with_children_and_an_empty_instruction_prints_no_parent_instruction() -> None:
    document = _document(
        [_question(1), _question(2)],
        (_part(place=0, children=("item_001", "item_002")),),
    )

    result = native_exam_to_pdf_document(document)

    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert result.html.count(_PARENT_DIV) == 0
    assert result.html.count(_PART_SECTION) == 0


def test_a_part_with_children_prints_its_instruction_once_before_its_first_child() -> None:
    document = _document(
        [_question(1), _question(2)],
        (_part(place=0, instruction=_PART_TEXT, children=("item_001", "item_002")),),
    )

    result = native_exam_to_pdf_document(document)

    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert result.html.count(_PARENT_DIV) == 1
    assert result.html.count(_PART_TEXT) == 1
    assert result.html.count(_PART_SECTION) == 0
    first_item, second_item = _section_positions(result.html)
    parent_at = result.html.index(_PARENT_DIV)
    assert first_item < parent_at < second_item


def test_a_childless_part_at_place_zero_comes_before_the_first_question() -> None:
    document = _document(
        [_question(1), _question(2)],
        (_part(place=0, instruction=_PART_TEXT),),
    )

    result = native_exam_to_pdf_document(document)

    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert result.html.index(_PART_SECTION) < _section_positions(result.html)[0]
