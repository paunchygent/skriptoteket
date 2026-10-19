"""Decision D4: dropdown options keep the teacher's stored order in every export."""

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
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import qti_tag
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    entry_blocks,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_payload,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body

# Stored order is neither id order nor alphabetical; the correct option is neither
# first stored nor alphabetically first.
_STORED = (("choice_003", "Öland"), ("choice_001", "Gotland"), ("choice_002", "Ven"))
_CORRECT_ID = "choice_002"
_LABELS = [label for _, label in _STORED]


def _item() -> NativeExamItem:
    payload = inline_choice_payload()
    payload["body"] = [
        {
            "heading_level": None,
            "segments": [
                {"kind": "text", "text": "Ön: ", "marks": []},
                {"kind": "gap", "gap_id": "gap_001"},
            ],
        }
    ]
    payload["gaps"] = [
        {
            "gap_id": "gap_001",
            "options": [
                {
                    "choice_id": choice_id,
                    "body": [p.model_dump(mode="json") for p in plain_body(label)],
                }
                for choice_id, label in _STORED
            ],
            "correct_option_id": _CORRECT_ID,
        }
    ]
    return NativeExamItem.model_validate(payload)


def test_qti_dropdown_options_keep_stored_order_without_shuffle() -> None:
    (qti,) = native_exam_to_examnet_qti_items(document_of((_item(),)))
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti))
    (interaction,) = root.iter(qti_tag("qti-inline-choice-interaction"))
    assert interaction.attrib["shuffle"] == "false"
    choices = interaction.findall(qti_tag("qti-inline-choice"))
    assert [
        (choice.attrib["identifier"], "".join(choice.itertext()).strip()) for choice in choices
    ] == list(_STORED)
    (declaration,) = root.iter(qti_tag("qti-response-declaration"))
    correct = declaration.findall(f"{qti_tag('qti-correct-response')}/{qti_tag('qti-value')}")
    assert [value.text for value in correct] == [_CORRECT_ID]


def test_pdf_dropdown_options_render_in_stored_order() -> None:
    plan = native_exam_to_pdf_document(document_of((_item(),)))
    assert plan.status is DigiExamExamNetPdfStatus.SUCCESS
    prompt, key = plan.html.split('<p class="answer-key">', maxsplit=1)
    assert "Ön: [Öland / Gotland / Ven]" in prompt
    positions = [prompt.index(escape(label)) for label in _LABELS]
    assert positions == sorted(positions)
    assert all(prompt.count(escape(label)) == 1 for label in _LABELS)
    assert escape("Ven") in key
    assert escape("Öland") not in key
    assert escape("Gotland") not in key


def test_docx_dropdown_brackets_options_in_stored_order_and_facit_key_correct() -> None:
    document = document_of((_item(),))
    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(document)
    with ZipFile(BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    text = "\n".join(
        "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        for paragraph in root.findall(".//w:p", ns)
    )
    assert "Ön: [Öland / Gotland / Ven]" in text
    assert "Facit" not in text

    facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
    key_lines = [
        line
        for entry in facit.entries
        for block in entry_blocks(entry)
        if isinstance(block, PrintAnswerKey)
        for line in block.lines
    ]
    assert "Lucka 1: Ven" in key_lines
    assert not any("Öland" in line or "Gotland" in line for line in key_lines)
