"""Regression tests for deterministic DigiExam title and image repairs."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
    DigiExamWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)

pytestmark = pytest.mark.unit

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


def test_unresolved_prompt_image_positions_stay_non_blocking_in_parser_and_ir() -> None:
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
    assert exam.renderer_ready is True
    assert len(exam.warnings) >= 1


def test_referenced_invalid_image_payload_stays_non_blocking_in_parser() -> None:
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


def test_missing_and_blank_titles_keep_question_n_fallback() -> None:
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
