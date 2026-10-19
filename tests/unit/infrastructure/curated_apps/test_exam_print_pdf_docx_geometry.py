"""The print PDF body uses the DOCX house geometry (TASK-SKRIPT-40-04-07 R2.1).

The WeasyPrint user-agent stylesheet keeps an 8 px body margin unless the house CSS
removes it. This test lays out the real STUDENT print HTML and compares the body's
content box against the DOCX section the production writer emits for the same native
document, so a CSS-string match alone cannot pass it.
"""

import io
from collections.abc import Iterator

import pytest
from docx import Document
from docx.shared import Emu
from weasyprint import HTML
from weasyprint.formatting_structure.boxes import Box

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

_PX_TO_MM = 25.4 / 96
_TOLERANCE_MM = 0.3


def _px_to_mm(px: float) -> float:
    return px * _PX_TO_MM


def _walk(box: Box) -> Iterator[Box]:
    yield box
    for child in box.children:
        yield from _walk(child)


def _class_list(box: Box) -> list[str]:
    element = box.element
    if element is None:
        return []
    classes = element.get("class")
    if classes is None:
        return []
    return classes.split()


def test_print_pdf_body_matches_the_docx_section_geometry() -> None:
    native = make_document(make_free_text_item())
    writer = exam_workspace_docx_writer.ExamWorkspaceDocxWriter()
    parsed = Document(io.BytesIO(writer.build_docx_bytes(native)))
    section = parsed.sections[0]
    page_width = section.page_width
    left_margin = section.left_margin
    right_margin = section.right_margin
    top_margin = section.top_margin
    assert page_width is not None
    assert left_margin is not None
    assert right_margin is not None
    assert top_margin is not None

    html = render_print_html(
        build_print_document(native, variant=ExamPrintVariant.STUDENT),
        assets=native.assets,
        assets_by_id={},
    )
    page_box = HTML(string=html).render().pages[0]._page_box
    body = next(box for box in _walk(page_box) if box.element_tag == "body")

    assert _px_to_mm(body.content_box_x()) == pytest.approx(left_margin.mm, abs=_TOLERANCE_MM)
    assert _px_to_mm(body.content_box_y()) == pytest.approx(top_margin.mm, abs=_TOLERANCE_MM)
    assert _px_to_mm(body.width) == pytest.approx(
        Emu(page_width - left_margin - right_margin).mm, abs=_TOLERANCE_MM
    )


def test_print_pdf_writing_lines_span_the_body_content_width() -> None:
    native = make_document(make_free_text_item())
    html = render_print_html(
        build_print_document(native, variant=ExamPrintVariant.STUDENT),
        assets=native.assets,
        assets_by_id={},
    )
    page_box = HTML(string=html).render().pages[0]._page_box
    body = next(box for box in _walk(page_box) if box.element_tag == "body")
    line = next(
        box
        for box in _walk(page_box)
        if box.element_tag == "div" and "writing-line" in _class_list(box)
    )

    assert _px_to_mm(line.width) == pytest.approx(_px_to_mm(body.width), abs=_TOLERANCE_MM)
