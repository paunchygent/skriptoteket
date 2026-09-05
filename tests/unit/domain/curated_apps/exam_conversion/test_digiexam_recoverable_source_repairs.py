"""Regression tests for deterministic DigiExam title and image repairs."""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyEnrichmentPlanState,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
    DigiExamWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
    build_digiexam_ir_manifest,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_prompt_repair import (
    PROMPT_IMAGE_PLACEHOLDER_LINE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

pytestmark = pytest.mark.unit

_WRITER = ExamNetQtiPackageWriter()

CANONICAL_TITLE_MESSAGE_FOR_QUESTION_1 = (
    "Fråga 1 saknade titel. "
    "Titeln ”Question 1” lades till automatiskt. "
    "Kontrollera titeln innan du använder provet."
)
CANONICAL_TITLE_MESSAGE_FOR_QUESTION_3 = (
    "Fråga 3 saknade titel. "
    "Titeln ”Question 3” lades till automatiskt. "
    "Kontrollera titeln innan du använder provet."
)
CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1 = (
    "Bilden i fråga 1 saknas. Lägg till den innan du använder provet."
)
CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_3 = (
    "Bilden i fråga 3 saknas. Lägg till den innan du använder provet."
)


def _missing_image_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Bild saknas i frågan",
                        "about": "Titta på bilden och svara.",
                        "bodyHTML": (
                            "<p>Titta på bilden och svara.</p>"
                            '<p><img class="fr-fic"/></p>'
                            '<p><img data-image-id="0" class="fr-fic" /></p>'
                        ),
                        "images": [],
                        "maxScore": 2,
                        "type": 0,
                    }
                ]
            }
        ]
    }


def _fractional_payload() -> dict[str, object]:
    questions = []
    for index in range(1, 5):
        questions.append(
            {
                "id": index,
                "title": f"Fråga {index}",
                "about": "Svara.",
                "bodyHTML": "<p>Svara.</p>",
                "images": [],
                "maxScore": 1,
                "type": 0,
            }
        )
    return {"exams": [{"questions": questions}]}


def _missing_title_payload(*, blank: bool) -> dict[str, object]:
    question: dict[str, object] = {
        "id": 1,
        "about": "Svara.",
        "bodyHTML": "<p>Svara.</p>",
        "images": [],
        "maxScore": 1,
        "type": 0,
    }
    if blank:
        question["title"] = "  "
    return {"exams": [{"questions": [question]}]}


def _item_xml(plan, item_filename: str) -> ElementTree.Element:
    item_file = next(file for file in plan.files if file.relative_path == f"items/{item_filename}")
    return ElementTree.fromstring(item_file.payload)


def test_unresolved_prompt_image_positions_become_pdf_placeholder_without_blocking() -> None:
    result = DigiExamDxeParser().parse_payload(
        _missing_image_payload(), filename="missing-image.dxe"
    )

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    image_warnings = [
        warning
        for warning in result.items[0].warnings
        if warning.code == DigiExamWarningCode.MISSING_PROMPT_IMAGE
    ]
    assert len(image_warnings) == 1
    assert image_warnings[0].blocking is False
    assert image_warnings[0].message == CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1

    exam = build_digiexam_intermediate_exam(result)
    manifest = build_digiexam_ir_manifest(exam)
    assert manifest.renderer_ready is True
    assert manifest.warning_count >= 1

    document = build_digiexam_examnet_pdf_document(exam)
    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert document.html.count(PROMPT_IMAGE_PLACEHOLDER_LINE) == 2
    assert "missing-image-placeholder" in document.html
    assert not any(warning.blocking for warning in document.warnings)


def test_referenced_invalid_image_payload_becomes_placeholder_without_blocking() -> None:
    payload = _missing_image_payload()
    exams = payload["exams"]
    assert isinstance(exams, list)
    exam_payload = exams[0]
    assert isinstance(exam_payload, dict)
    questions = exam_payload["questions"]
    assert isinstance(questions, list)
    question = questions[0]
    assert isinstance(question, dict)
    question["bodyHTML"] = '<p><img data-image-id="0" /></p>'
    question["images"] = ["invalid"]

    result = DigiExamDxeParser().parse_payload(payload, filename="invalid-image.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_assets == ()
    assert result.items[0].embedded_asset_references == ()
    assert [warning.code for warning in result.items[0].warnings] == [
        DigiExamWarningCode.MISSING_PROMPT_IMAGE
    ]
    assert result.items[0].warnings[0].message == CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1
    document = build_digiexam_examnet_pdf_document(build_digiexam_intermediate_exam(result))
    assert document.html.count(PROMPT_IMAGE_PLACEHOLDER_LINE) == 1


def test_source_repairs_do_not_admit_an_additional_provider_candidate() -> None:
    payload = {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "  ",
                        "about": "Välj ett svar.",
                        "bodyHTML": '<p>Välj ett svar.</p><img data-image-id="0" />',
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alfa", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": False},
                        ],
                    }
                ]
            }
        ]
    }
    repaired_exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(payload, filename="repair-provider-free.dxe")
    )

    plan = plan_answer_key_enrichment(repaired_exam)

    assert plan.state == AnswerKeyEnrichmentPlanState.BLOCKED
    assert plan.unkeyed_items == ()
    assert {
        DigiExamWarningCode.MISSING_QUESTION_TITLE,
        DigiExamWarningCode.MISSING_PROMPT_IMAGE,
    }.issubset({warning.code for warning in repaired_exam.items[0].warnings})


def test_unresolved_prompt_image_positions_become_qti_placeholder_without_resource() -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(_missing_image_payload(), filename="missing-image.dxe")
    )
    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    plan = build_examnet_qti_package_plan(
        package_name="missing-image",
        items=adapter_result.items,
    )
    zip_bytes = _WRITER.build_package_bytes(plan)

    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    assert plan.warnings == ()
    assert adapter_result.items[0].image_resources == ()
    assert adapter_result.items[0].prompt_lines.count(PROMPT_IMAGE_PLACEHOLDER_LINE) == 2

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert not any(name.startswith("resources/") for name in names)
        manifest = archive.read("imsmanifest.xml").decode("utf-8")
        item_xml = archive.read("items/item_001.xml").decode("utf-8")

    assert "resources/" not in manifest
    assert "resources/" not in item_xml
    assert "<img" not in item_xml
    item = ElementTree.fromstring(item_xml.encode("utf-8"))
    prompt_text = " ".join("".join(item.itertext()).split())
    assert PROMPT_IMAGE_PLACEHOLDER_LINE in prompt_text

    report = build_examnet_qti_validation_report(
        plan=plan,
        package_filename="qti-package.zip",
        package_bytes=zip_bytes,
    )
    assert report.package_status == ExamNetQtiPackageStatus.PASSED
    assert report.errors == ()


def test_source_repair_messages_carry_real_question_numbers_and_no_literal_n() -> None:
    payload = _fractional_payload()
    exams = payload["exams"]
    assert isinstance(exams, list)
    exam = exams[0]
    assert isinstance(exam, dict)
    questions = exam["questions"]
    assert isinstance(questions, list)
    third = questions[2]
    assert isinstance(third, dict)
    third["title"] = "  "
    third["bodyHTML"] = '<p>Välj alla rätta.</p><p><img class="fr-fic"/></p>'
    third["images"] = []

    first_result = DigiExamDxeParser().parse_payload(payload, filename="repair-numbers.dxe")
    second_result = DigiExamDxeParser().parse_payload(payload, filename="repair-numbers.dxe")

    title_warnings = [
        warning
        for warning in first_result.items[2].warnings
        if warning.code == DigiExamWarningCode.MISSING_QUESTION_TITLE
    ]
    image_warnings = [
        warning
        for warning in first_result.items[2].warnings
        if warning.code == DigiExamWarningCode.MISSING_PROMPT_IMAGE
    ]
    assert len(title_warnings) == 1
    assert len(image_warnings) == 1
    assert title_warnings[0].message == CANONICAL_TITLE_MESSAGE_FOR_QUESTION_3
    assert image_warnings[0].message == CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_3
    assert first_result.items[2].header == "Question 3"
    for warning in (*title_warnings, *image_warnings):
        assert warning.blocking is False
        assert "N" not in warning.message
        assert "{question_number}" not in warning.message
    assert first_result.items[2].warnings == second_result.items[2].warnings


def test_missing_and_blank_titles_keep_question_n_fallback_in_pdf_and_qti() -> None:
    for blank in (False, True):
        parse_result = DigiExamDxeParser().parse_payload(
            _missing_title_payload(blank=blank),
            filename="missing-title.dxe",
        )
        assert parse_result.status == DigiExamParseStatus.SUCCESS
        assert parse_result.renderer_ready is True
        item = parse_result.items[0]
        assert item.header == "Question 1"
        title_warnings = [
            warning
            for warning in item.warnings
            if warning.code == DigiExamWarningCode.MISSING_QUESTION_TITLE
        ]
        assert len(title_warnings) == 1
        assert title_warnings[0].blocking is False
        assert title_warnings[0].message == CANONICAL_TITLE_MESSAGE_FOR_QUESTION_1
        assert "{question_number}" not in title_warnings[0].message

        exam = build_digiexam_intermediate_exam(parse_result)
        assert exam.items[0].title == "Question 1"

        document = build_digiexam_examnet_pdf_document(exam)
        assert document.status == DigiExamExamNetPdfStatus.SUCCESS

        qti_result = build_examnet_qti_items_from_digiexam_ir(exam)
        plan = build_examnet_qti_package_plan(
            package_name=f"missing-title-{blank}",
            items=qti_result.items,
        )
        assert plan.status == ExamNetQtiPackageStatus.PASSED
        item_root = _item_xml(plan, "item_001.xml")
        assert item_root.attrib["title"] == "Question 1"
