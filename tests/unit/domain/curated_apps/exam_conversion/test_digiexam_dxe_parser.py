"""Tests for the DigiExam `.dxe` parser contract.

Purpose:
    Prove fixture-backed `.dxe` parsing, canonical structure extraction, and
    fail-closed enrichment rules, ported from Sir Convert-a-Lot at revision
    41be61a6.

Relationships:
    - Exercises `domain.curated_apps.exam_conversion.digiexam_dxe_parser` as
      the `.dxe` parser boundary.
    - Result-PDF text extraction (pymupdf) stays deferred in this walking
      skeleton; evidence-path rules are exercised with typed evidence values.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
    DigiExamParseStatus,
    DigiExamWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerItem,
)

pytestmark = pytest.mark.unit

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE = _FIXTURE_DIR / "1772718003-test-samma-prov-i-digiexam.dxe"
_DUPLICATE_DXE = _FIXTURE_DIR / "1772718003-test-duplicate.dxe"
_EMBEDDED_IMAGE_DXE = _FIXTURE_DIR / "sanitized-embedded-image.dxe"
_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mNk+M9QDwADhgGA"
    "WjR9awAAAABJRU5ErkJggg=="
)


def test_dxe_fixture_preserves_exact_observed_structure_without_answer_synthesis() -> None:
    result = DigiExamDxeParser().parse_file(_DXE)

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.metadata.filename == _DXE.name
    assert result.metadata.producer == "DigiExam .dxe"
    assert len(result.items) == 7
    assert [item.digiexam_type_code for item in result.items] == [0, 1, 1, 2, 2, 2, 3]
    assert [item.max_score for item in result.items] == [5, 2, 2, 2, 4, 6, 3]
    assert [item.item_type for item in result.items] == [
        DigiExamItemType.OPEN_ENDED,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    ]
    assert [item.header for item in result.items] == [
        "Fritextfråga",
        "Flervalsfråga typ 1",
        "Ytterligare en flervalsfråga",
        "Flera rätta svar (flervalsfråga)",
        "Fråga 5",
        "Fråga 6",
        "Lucktext",
    ]

    machine_marked = result.items[1:]
    assert all(
        item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT for item in machine_marked
    )
    assert all(item.correct_alternative_ids == () for item in machine_marked)
    assert all(item.correct_gap_values == () for item in machine_marked)
    assert all(item.embedded_assets == () for item in result.items)
    assert all(item.embedded_asset_references == () for item in result.items)


def test_dxe_fixture_preserves_alternatives_gaps_and_grading_policy() -> None:
    result = DigiExamDxeParser().parse_file(_DXE)
    items = {item.header: item for item in result.items}

    first_mcq = items["Flervalsfråga typ 1"]
    assert [alternative.id for alternative in first_mcq.alternatives] == [1, 2, 3, 4, 5]
    assert [alternative.title for alternative in first_mcq.alternatives] == [
        "Första alternativet ",
        "Andra alternativet",
        "Tredje alternativet",
        "Fjärde alternativet",
        "Ytterligare ett alternativ. Man kan lägga till hur många man vill",
    ]
    assert [alternative.right for alternative in first_mcq.alternatives] == [
        False,
        False,
        False,
        False,
        False,
    ]

    question_6 = items["Fråga 6"]
    assert question_6.grading_policy is not None
    assert question_6.grading_policy.grading_type == 2
    assert question_6.grading_policy.is_alternative_choice_limit_enabled is True
    assert question_6.grading_policy.alternative_choice_limit == 2

    gap_item = items["Lucktext"]
    assert [gap.guid for gap in gap_item.gaps] == [
        "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
        "21d786a3-2f14-49f1-8ffc-388f06d9a20c",
        "b011fc52-c9b2-4d74-aa78-e94035e0599b",
    ]
    assert [gap.validations for gap in gap_item.gaps] == [(), (), ()]


def test_duplicate_dxe_fixture_proves_same_question_shape() -> None:
    parser = DigiExamDxeParser()
    primary = parser.parse_file(_DXE)
    duplicate = parser.parse_file(_DUPLICATE_DXE)

    assert [item.question_id for item in duplicate.items] == [
        item.question_id for item in primary.items
    ]
    assert [item.header for item in duplicate.items] == [item.header for item in primary.items]
    assert [item.digiexam_type_code for item in duplicate.items] == [
        item.digiexam_type_code for item in primary.items
    ]
    assert [item.max_score for item in duplicate.items] == [
        item.max_score for item in primary.items
    ]


def test_dxe_embedded_image_fixture_binds_renderer_neutral_asset_to_body_html() -> None:
    result = DigiExamDxeParser().parse_file(_EMBEDDED_IMAGE_DXE)

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    item = result.items[0]
    asset = item.embedded_assets[0]
    reference = item.embedded_asset_references[0]
    decoded = base64.b64decode(_PNG_BASE64, validate=True)

    assert len(item.embedded_assets) == 1
    assert asset.asset_id.startswith("item-001-asset-001-")
    assert asset.source_image_index == 0
    assert asset.sha256 == hashlib.sha256(decoded).hexdigest()
    assert asset.media_type == "image/png"
    assert base64.b64decode(asset.content_base64, validate=True) == decoded
    assert asset.byte_length == len(decoded)
    assert asset.width_px == 1
    assert asset.height_px == 1
    assert reference.asset_id == asset.asset_id
    assert reference.source_image_index == 0
    assert reference.reference_order == 1


def test_repeated_dxe_embedded_image_references_are_valid_ordered_references() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["bodyHTML"] = (
        '<p><img data-image-id="0" /></p><p><img data-image-id="0" /></p>'
    )

    result = DigiExamDxeParser().parse_payload(payload, filename="repeated-image.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert len(result.items[0].embedded_assets) == 1
    assert [
        reference.reference_order for reference in result.items[0].embedded_asset_references
    ] == [1, 2]
    assert {reference.asset_id for reference in result.items[0].embedded_asset_references} == {
        result.items[0].embedded_assets[0].asset_id
    }


@pytest.mark.parametrize("invalid_payload", ["not valid base64", "aGVsbG8="])
def test_referenced_invalid_embedded_asset_stays_exportable_with_placeholder_warning(
    invalid_payload: str,
) -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["images"][0] = invalid_payload

    result = DigiExamDxeParser().parse_payload(payload, filename="invalid-image.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_assets == ()
    image_warnings = [
        warning
        for warning in result.items[0].warnings
        if warning.code == DigiExamWarningCode.MISSING_PROMPT_IMAGE
    ]
    assert len(image_warnings) == 1
    assert image_warnings[0].message == (
        "Bilden i fråga 1 saknas. Lägg till den innan du använder provet."
    )
    warning_codes = {warning.code for warning in result.items[0].warnings}
    assert DigiExamWarningCode.INVALID_EMBEDDED_ASSET_BASE64 not in warning_codes
    assert DigiExamWarningCode.UNSUPPORTED_EMBEDDED_ASSET_MEDIA not in warning_codes


def test_missing_embedded_asset_reference_stays_exportable_with_item_warning() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["images"] = []
    payload["exams"][0]["questions"][0]["bodyHTML"] = '<p><img data-image-id="1" /></p>'

    result = DigiExamDxeParser().parse_payload(payload, filename="missing-image-ref.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.MISSING_PROMPT_IMAGE in {warning.code for warning in result.warnings}
    image_warning = next(
        warning
        for warning in result.items[0].warnings
        if warning.code == DigiExamWarningCode.MISSING_PROMPT_IMAGE
    )
    assert image_warning.message == (
        "Bilden i fråga 1 saknas. Lägg till den innan du använder provet."
    )
    assert all(
        not warning.blocking
        for warning in result.warnings
        if warning.code == DigiExamWarningCode.MISSING_PROMPT_IMAGE
    )


def test_empty_embedded_asset_payloads_with_body_reference_stay_exportable() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["images"] = []
    payload["exams"][0]["questions"][0]["bodyHTML"] = '<p><img data-image-id="0" /></p>'

    result = DigiExamDxeParser().parse_payload(payload, filename="empty-images-ref.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_assets == ()
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.MISSING_PROMPT_IMAGE in {warning.code for warning in result.warnings}


def test_missing_embedded_asset_payloads_with_body_reference_stay_exportable() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    del payload["exams"][0]["questions"][0]["images"]
    payload["exams"][0]["questions"][0]["bodyHTML"] = '<p><img data-image-id="0" /></p>'

    result = DigiExamDxeParser().parse_payload(payload, filename="missing-images-ref.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_assets == ()
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.MISSING_PROMPT_IMAGE in {warning.code for warning in result.warnings}


def test_orphan_prompt_image_position_stays_exportable_with_item_warning() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["images"] = []
    payload["exams"][0]["questions"][0]["bodyHTML"] = (
        '<p><img class="fr-fic"/></p><p>Rests of the prompt.</p>'
    )

    result = DigiExamDxeParser().parse_payload(payload, filename="orphan-image.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].embedded_assets == ()
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.MISSING_PROMPT_IMAGE in {warning.code for warning in result.warnings}


def test_unused_embedded_asset_payload_fails_closed_with_typed_warning() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["bodyHTML"] = "<p>No image reference.</p>"

    result = DigiExamDxeParser().parse_payload(payload, filename="unused-image.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.UNUSED_EMBEDDED_ASSET_PAYLOAD in {
        warning.code for warning in result.warnings
    }


def test_ambiguous_embedded_asset_binding_fails_closed_with_typed_warning() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["bodyHTML"] = (
        '<p><img data-image-id="0" data-image-id="1" /></p>'
    )

    result = DigiExamDxeParser().parse_payload(payload, filename="ambiguous-image-ref.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].embedded_asset_references == ()
    assert DigiExamWarningCode.AMBIGUOUS_EMBEDDED_ASSET_BINDING in {
        warning.code for warning in result.warnings
    }


def test_typed_evidence_duplicate_alternative_labels_fail_closed() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][1]["alternatives"][0]["title"] = "Andra alternativet"

    result = DigiExamDxeParser().parse_payload(
        payload,
        filename="duplicate-answer-label.dxe",
        answer_evidence=DigiExamResultPdfAnswerEvidence(
            items=(
                DigiExamResultPdfAnswerItem(
                    title="Flervalsfråga typ 1",
                    correct_alternative_texts=("Andra alternativet",),
                    correct_gap_values=(),
                ),
            )
        ),
    )

    item = result.items[1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.correct_alternative_ids == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_typed_evidence_unmatched_alternative_label_fails_closed() -> None:
    result = DigiExamDxeParser().parse_file(
        _DXE,
        answer_evidence=DigiExamResultPdfAnswerEvidence(
            items=(
                DigiExamResultPdfAnswerItem(
                    title="Flervalsfråga typ 1",
                    correct_alternative_texts=("Inte korrekt label",),
                    correct_gap_values=(),
                ),
            )
        ),
    )

    item = result.items[1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.correct_alternative_ids == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_result_pdf_gap_answer_count_mismatch_fails_closed_without_enrichment() -> None:
    evidence = DigiExamResultPdfAnswerEvidence(
        items=(
            DigiExamResultPdfAnswerItem(
                title="Lucktext",
                correct_alternative_texts=(),
                correct_gap_values=("lucktext",),
            ),
        )
    )

    result = DigiExamDxeParser().parse_file(_DXE, answer_evidence=evidence)

    item = result.items[-1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.header == "Lucktext"
    assert item.correct_gap_values == ()
    assert item.correct_gap_answers == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_populated_dxe_right_flags_are_treated_as_dxe_answer_key_provenance() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = True

    result = DigiExamDxeParser().parse_payload(payload, filename="populated.dxe")

    item = result.items[1]
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY
    assert item.correct_alternative_ids == (2,)


def test_unsupported_dxe_question_type_fails_closed() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["type"] = 99

    result = DigiExamDxeParser().parse_payload(payload, filename="unknown-type.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].item_type == DigiExamItemType.UNKNOWN
    assert DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE in {warning.code for warning in result.warnings}


def test_malformed_dxe_payload_fails_closed_without_untyped_exception() -> None:
    result = DigiExamDxeParser().parse_text("{", filename="broken.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items == ()
    assert result.warnings[0].code == DigiExamWarningCode.MALFORMED_SOURCE


def test_missing_required_dxe_sections_fail_closed_without_untyped_exception() -> None:
    result = DigiExamDxeParser().parse_payload(
        {"exams": [{"title": "Broken"}]}, filename="missing.dxe"
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items == ()
    assert result.warnings[0].code == DigiExamWarningCode.MALFORMED_SOURCE
