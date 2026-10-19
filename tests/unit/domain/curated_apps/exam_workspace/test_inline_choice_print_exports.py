"""Printable exports must not silently discard dropdown options or the keyed label."""

from html import escape
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)


def test_docx_preserves_gap_local_lists_and_facit_keys_in_placed_order() -> None:
    document = document_of((inline_choice_item(),))
    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(document)
    with ZipFile(BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines = [
        "".join(node.itertext())
        for paragraph in root.findall(".//w:p", ns)
        for node in paragraph.findall("w:r/w:t", ns)
    ]
    text = "\n".join(lines)
    assert "Facit" not in text
    for label in ("Beta", "Alfa"):
        for option in (1, 2, 3):
            assert f"{label} {option} & <text>" in text
    assert text.index("Beta 1 & <text>") < text.index("Alfa 1 & <text>")

    facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
    key_lines = [
        line
        for entry in facit.entries
        for block in entry.blocks
        if isinstance(block, PrintAnswerKey)
        for line in block.lines
    ]
    assert "Lucka 1: Beta 2 & <text>" in key_lines
    assert "Lucka 2: Alfa 1 & <text>" in key_lines
    assert not any("choice_001" in line or "choice_002" in line for line in key_lines)


def test_pdf_plan_preserves_options_and_actual_key_labels_not_raw_ids() -> None:
    plan = native_exam_to_pdf_document(document_of((inline_choice_item(),)))
    assert plan.status is DigiExamExamNetPdfStatus.SUCCESS
    prompt, key = plan.html.split('<div class="answer-key">', maxsplit=1)
    for label in ("Beta", "Alfa"):
        for option in (1, 2, 3):
            assert escape(f"{label} {option} & <text>") in prompt
    assert prompt.index("Beta 1") < prompt.index("Alfa 1")
    assert escape("Beta 2 & <text>") in key
    assert escape("Alfa 1 & <text>") in key
    assert escape("Alfa 2 & <text>") not in key
    assert escape("Beta 1 & <text>") not in key
    assert "choice_001" not in key
