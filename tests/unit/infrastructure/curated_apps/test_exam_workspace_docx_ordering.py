"""Ordering items list steps in print order behind a box and keep the key in the facit."""

import io

from docx import Document

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
    make_paragraph,
)


def _paragraphs(*, english: bool = False) -> list[str]:
    item = make_ordering_item()
    if english:
        item = item.model_copy(
            update={"body": (make_paragraph("Put the steps of what is an essay in order."),)}
        )
    content = ExamWorkspaceDocxWriter().build_docx_bytes(make_document(item))
    ExamWorkspaceDocxWriter().validate_docx_bytes(content, expected_item_count=1)
    return [paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs]


def test_steps_follow_print_order_with_boxes() -> None:
    lines = _paragraphs()
    boxed = [line for line in lines if line.startswith("☐ ")]
    assert boxed == ["☐ Avslutning", "☐ Motargument", "☐ Argument", "☐ Tes"]


def test_facit_line_names_each_step_with_its_key_number() -> None:
    lines = _paragraphs(english=True)
    facit = [line for line in lines if "Avslutning 4" in line]
    assert facit == ["Rätt ordning: Avslutning 4; Motargument 3; Argument 2; Tes 1"]


def test_swedish_label() -> None:
    assert "Rätt ordning: Avslutning 4; Motargument 3; Argument 2; Tes 1" in _paragraphs()
