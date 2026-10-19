"""Ordering items list steps in print order behind a box and keep the key in the facit."""

import io

from docx import Document
from docx.text.paragraph import Paragraph

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    entry_blocks,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
    make_paragraph,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    NBSP,
    run_border,
)

_FACIT_LINE = "Rätt ordning: Avslutning 4; Motargument 3; Argument 2; Tes 1"


def _item(*, english: bool = False) -> NativeExamItem:
    item = make_ordering_item()
    if english:
        item = item.model_copy(
            update={"body": (make_paragraph("Put the steps of what is an essay in order."),)}
        )
    return item


def _paragraphs(*, english: bool = False) -> list[str]:
    return [paragraph.text for paragraph in _document_paragraphs(english=english)]


def _document_paragraphs(*, english: bool = False) -> list[Paragraph]:
    content = ExamWorkspaceDocxWriter().build_docx_bytes(make_document(_item(english=english)))
    ExamWorkspaceDocxWriter().validate_docx_bytes(content, expected_item_count=1)
    return list(Document(io.BytesIO(content)).paragraphs)


def _facit_lines(*, english: bool = False) -> list[str]:
    facit = build_print_document(
        make_document(_item(english=english)), variant=ExamPrintVariant.FACIT
    )
    return [
        line
        for entry in facit.entries
        for block in entry_blocks(entry)
        if isinstance(block, PrintAnswerKey)
        for line in block.lines
    ]


def test_steps_follow_print_order_with_boxes() -> None:
    paragraphs = _document_paragraphs()
    boxed = [
        paragraph
        for paragraph in paragraphs
        if paragraph.runs and run_border(paragraph.runs[0]) is not None
    ]
    assert [paragraph.runs[-1].text for paragraph in boxed] == [
        "Avslutning",
        "Motargument",
        "Argument",
        "Tes",
    ]
    for paragraph in boxed:
        border = run_border(paragraph.runs[0])
        assert border is not None and border["val"] == "single"
        assert paragraph.runs[0].text != "" and set(paragraph.runs[0].text) == {NBSP}
    assert all("☐" not in paragraph.text for paragraph in paragraphs)


def test_facit_line_names_each_step_with_its_key_number() -> None:
    facit = [line for line in _facit_lines(english=True) if "Avslutning 4" in line]
    assert facit == [_FACIT_LINE]


def test_swedish_label() -> None:
    assert _FACIT_LINE in _facit_lines()
    assert _FACIT_LINE not in _paragraphs()
