"""Tests for the DigiExam Exam.net PDF renderer.

Purpose:
    Prove that DigiExam IR can render to the promoted Exam.net PDF-converter
    shape with fail-closed warnings and live PDF generation for embedded
    images, ported from Sir Convert-a-Lot at revision 41be61a6.

Relationships:
    - Exercises the SRP Exam.net PDF domain renderer modules.
    - Uses WeasyPrint through the in-process Exam.net PDF renderer seam for
      live artifact validation, asserted with pypdf instead of pymupdf.
"""

from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamGapAnswer,
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_items import (
    render_examnet_pdf_items,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrAnswerKey,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_item_strategies import (
    ExamNetPdfItemLabelPolicy,
    ExamNetPdfTargetProfileContext,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)

pytestmark = pytest.mark.unit

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_EMBEDDED_IMAGE_DXE = _FIXTURE_DIR / "sanitized-embedded-image.dxe"


def test_examnet_pdf_document_uses_promoted_converter_shape_without_option_labels() -> None:
    exam = _exam_from_payload(_renderable_payload(), filename="renderable.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "Points:" not in document.html
    assert "Poängvärde: 2" in document.html
    assert "Typ: Fritext" in document.html
    assert "Skriv ditt svar i Exam.net." not in document.html
    assert "Type: Multiple choice" in document.html
    assert "Choose one answer" not in document.html
    assert "<p>Alpha</p>" in document.html
    assert "<p>Beta</p>" in document.html
    assert "Correct answer: Beta" in document.html
    assert "Type: Multiple response" in document.html
    assert "Choose all correct answers" not in document.html
    assert "Correct answers: First; Third" in document.html
    assert document.html.count("Typ: Fritext") == 1
    assert "Typ: Lucktext" in document.html
    assert "Type: Short answer" not in document.html
    assert "Correct answers: Stockholm; stockholm" in document.html
    assert "A. Alpha" not in document.html
    assert "<li>" not in document.html


def test_examnet_pdf_document_blocks_machine_marked_item_without_answer_key() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = False
    exam = _exam_from_payload(payload, filename="missing-key.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_missing_key_choice_blocked_without_export_state() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = False
    exam = _exam_from_payload(payload, filename="missing-key-accepted.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_multigap_blocked_without_key() -> None:
    exam = _multigap_exam()

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_manual_multigap_keys_in_lucktext_shape() -> None:
    exam = _multigap_exam()
    item = exam.items[0]
    answers = tuple(
        DigiExamGapAnswer(guid=gap.guid, value=f"facit {index}")
        for index, gap in enumerate(item.gaps, start=1)
    )
    keyed_item = replace(
        item,
        answer_key=DigiExamIrAnswerKey(
            provenance=DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY,
            correct_alternative_ids=(),
            correct_gap_answers=answers,
        ),
    )
    keyed_exam = replace(exam, items=(keyed_item,))

    document = build_digiexam_examnet_pdf_document(keyed_exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "Typ: Lucktext" in document.html
    assert "Type: Short answer" not in document.html
    assert "Correct answers:" in document.html
    assert "Lucka 1: facit 1" in document.html
    assert "Lucka 5: facit 5" in document.html
    assert "Manuell bedömning" not in document.html
    assert DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE not in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_target_profile_labels_do_not_mutate_ir_item_semantics() -> None:
    exam = _exam_from_payload(_renderable_payload(), filename="profile-labels.dxe")
    original_item = exam.items[0]
    target_context = ExamNetPdfTargetProfileContext(
        target_id="examnet_pdf",
        profile_version="test-profile",
        label_policy=ExamNetPdfItemLabelPolicy(free_text_type_label="Profile free text"),
    )

    result = render_examnet_pdf_items(
        exam=replace(exam, items=(original_item,)),
        asset_paths_by_reference={},
        target_profile_context=target_context,
    )

    assert not result.warnings
    assert result.items
    assert "Typ: Profile free text" in result.items[0].html
    assert exam.items[0].item_type == original_item.item_type
    assert exam.items[0].answer_key == original_item.answer_key


def test_examnet_pdf_document_strips_source_labelled_options_at_target_boundary() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][0]["title"] = "A. Alpha"
    payload["exams"][0]["questions"][1]["alternatives"][1]["title"] = "B) Beta"
    payload["exams"][0]["questions"][2]["alternatives"][0]["title"] = "1. First"
    payload["exams"][0]["questions"][2]["alternatives"][2]["title"] = "3) Third"
    exam = _exam_from_payload(payload, filename="labelled-options.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert document.warnings == ()
    assert "<p>Alpha</p>" in document.html
    assert "<p>Beta</p>" in document.html
    assert "Correct answer: Beta" in document.html
    assert "Correct answers: First; Third" in document.html
    assert "A. Alpha" not in document.html
    assert "B) Beta" not in document.html
    assert "1. First" not in document.html
    assert "3) Third" not in document.html


def test_examnet_pdf_document_blocks_duplicate_options_after_label_stripping() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][0]["title"] = "A. Alpha"
    payload["exams"][0]["questions"][1]["alternatives"][1]["title"] = "B. Alpha"
    exam = _exam_from_payload(payload, filename="duplicate-normalized-options.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH in {
        warning.code for warning in document.warnings
    }
    assert [
        warning.message
        for warning in document.warnings
        if warning.code == DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH
    ] == ["Item item-002 cannot render safely: duplicate option text is unsafe."]


def test_examnet_pdf_document_preserves_unsupported_source_type_warning() -> None:
    exam = _exam_from_payload(_renderable_payload(), filename="unsupported.dxe")
    unsupported_exam = replace(
        exam,
        items=(replace(exam.items[0], item_type=DigiExamItemType.UNKNOWN),),
    )

    document = build_digiexam_examnet_pdf_document(unsupported_exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert [
        warning.message
        for warning in document.warnings
        if warning.code == DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE
    ] == ["Item type unknown has no governed Exam.net PDF-converter target shape yet."]


def test_examnet_pdf_document_blocks_missing_embedded_asset_payload() -> None:
    exam = _embedded_image_open_ended_exam()
    item = exam.items[0]
    broken_asset = replace(item.embedded_assets[0], content_base64="")
    broken_item = replace(item, embedded_assets=(broken_asset,))
    broken_exam = replace(exam, items=(broken_item,))

    document = build_digiexam_examnet_pdf_document(broken_exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_MISSING in {
        warning.code for warning in document.warnings
    }


def test_live_examnet_pdf_renderer_generates_pdf_with_embedded_image() -> None:
    exam = _embedded_image_open_ended_exam()

    document = build_digiexam_examnet_pdf_document(exam)
    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "data-image-id" not in document.html
    assert len(document.asset_files) == 1

    pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=document)
    reader = PdfReader(BytesIO(pdf_bytes))

    assert len(reader.pages) == 1
    page = reader.pages[0]
    text = page.extract_text()
    assert "Fråga 1" in text
    assert "Poängvärde: 1" in text
    assert "Typ: Fritext" in text
    assert "Skriv ditt svar i Exam.net." not in text
    assert "Look at the embedded prompt image." in text
    assert page.images


def test_live_pdf_preserves_fractional_points_title_fallback_and_image_positions() -> None:
    exam = _exam_from_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": " ",
                            "about": "",
                            "bodyHTML": (
                                "<p>Besvara frågan.</p>"
                                '<p><img class="fr-fic"/></p>'
                                '<p><img data-image-id="0"/></p>'
                            ),
                            "images": [],
                            "maxScore": 0.25,
                            "type": 0,
                        }
                    ]
                }
            ]
        },
        filename="fractional-missing-images.dxe",
    )

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert exam.items[0].title == "Question 1"
    assert "Poängvärde: 0.25" in document.html
    assert document.html.count("Bild saknas – lägg till bilden innan du använder provet.") == 2
    assert not any(warning.blocking for warning in document.warnings)

    pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=document)
    reader = PdfReader(BytesIO(pdf_bytes))
    text = " ".join(page.extract_text() for page in reader.pages)

    assert pdf_bytes.startswith(b"%PDF")
    assert "Fråga 1" in text
    assert "Poängvärde: 0.25" in text
    assert text.count("Bild saknas") == 2


def _exam_from_payload(payload: object, *, filename: str) -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(payload, filename=filename)
    return build_digiexam_intermediate_exam(parse_result)


def _embedded_image_open_ended_exam() -> DigiExamIntermediateExam:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    question = payload["exams"][0]["questions"][0]
    question["title"] = "Embedded image prompt"
    question["about"] = "Look at the embedded prompt image."
    question["bodyHTML"] = (
        "<p>Look at the embedded prompt image.</p>"
        '<p><img data-image-id="0" class="fr-fic fr-dib" /></p>'
    )
    question["type"] = 0
    question["blanks"] = []
    return _exam_from_payload(payload, filename="embedded-open-ended.dxe")


def _multigap_exam() -> DigiExamIntermediateExam:
    payload = {
        "exams": [
            {
                "questions": [
                    {
                        "id": 13,
                        "title": "Lucktext med fem luckor",
                        "about": "",
                        "bodyHTML": "<p>Fyll i ___ ___ ___ ___ ___.</p>",
                        "images": [],
                        "maxScore": 5,
                        "type": 3,
                        "blanks": [
                            {"guid": f"gap-{index}", "validations": []} for index in range(1, 6)
                        ],
                    }
                ]
            }
        ]
    }
    return _exam_from_payload(payload, filename="multigap.dxe")


def _renderable_payload():
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Essay",
                        "about": "",
                        "bodyHTML": "<p>Explain the water cycle.</p>",
                        "images": [],
                        "maxScore": 3,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Single",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Multiple",
                        "about": "",
                        "bodyHTML": "<p>Choose the ordinal words.</p>",
                        "images": [],
                        "maxScore": 4,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "First", "about": "", "right": True},
                            {"id": 2, "title": "Between", "about": "", "right": False},
                            {"id": 3, "title": "Third", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 4,
                        "title": "Short",
                        "about": "",
                        "bodyHTML": "<p>Name Sweden's capital.</p>",
                        "images": [],
                        "maxScore": 1,
                        "type": 3,
                        "blanks": [
                            {
                                "guid": "gap-1",
                                "validations": ["Stockholm", "stockholm"],
                            }
                        ],
                    },
                ]
            }
        ]
    }
