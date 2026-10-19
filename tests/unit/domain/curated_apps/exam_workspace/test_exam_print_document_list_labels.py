"""Print headings use the question list labels, not running sequences (user rule 2026-10-19).

A part with children followed by a standalone question prints "Fråga 1a" and
"Fråga 1b" for the children and "Fråga 2" for the standalone question, even
though the running sequences are 1, 2 and 3. The print document feeds the
print preview, the student and facit PDFs and the DOCX student copy, so one
heading change reaches all four print outputs.
"""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintDocument,
    PrintHeading,
    PrintQuestion,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    free_text_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_paragraph,
)


def _part_document() -> NativeExamDocument:
    parent = NativeExamParent(
        parent_id="parent_001",
        place=0,
        instruction=(make_paragraph("Del 1"),),
        item_ids=("item_001", "item_002"),
    )
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(
            free_text_item(sequence=1, item_id="item_001"),
            free_text_item(sequence=2, item_id="item_002"),
            free_text_item(sequence=3, item_id="item_003"),
        ),
        parents=(parent,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _question_headings(document: PrintDocument) -> tuple[str, ...]:
    return tuple(
        block.text
        for entry in document.entries
        if isinstance(entry, PrintQuestion)
        for block in entry.text
        if isinstance(block, PrintHeading)
    )


def test_part_children_and_following_standalone_use_list_labels() -> None:
    student = build_print_document(_part_document(), variant=ExamPrintVariant.STUDENT)

    assert _question_headings(student) == ("Fråga 1a", "Fråga 1b", "Fråga 2")


def test_facit_headings_use_list_labels() -> None:
    facit = build_print_document(_part_document(), variant=ExamPrintVariant.FACIT)

    assert _question_headings(facit) == ("Fråga 1a", "Fråga 1b", "Fråga 2")
