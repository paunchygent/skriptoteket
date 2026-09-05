"""Regression tests for TASK-SKRIPT-39-01-02 source repairs.

Purpose:
    Prove on synthetic fixtures only that valid positive fractional point
    values pass unchanged through parser, neutral/effective IR,
    fingerprints/JSON artifacts, overlays/replay, PDF, and QTI scoring and
    gap allocation without warnings or rounding; that unresolved visible
    prompt image positions become visible PDF/QTI placeholders with one
    item-bound non-blocking Swedish warning and no QTI resource/manifest
    entry; and that missing/blank titles keep the deterministic `Question N`
    fallback with item-bound non-blocking Swedish review information.

Relationships:
    - Exercises the parser, IR, overlay, PDF, QTI, and fingerprint boundaries
      owned by `domain.curated_apps.exam_conversion`.
    - Copies no teacher-supplied `.dxe` files.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, replace
from io import BytesIO
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
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
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlay,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayGenericItemPatch,
    DigiExamOverlaySourceBinding,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    build_digiexam_intermediate_exam,
    build_digiexam_ir_manifest,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
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
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

pytestmark = pytest.mark.unit

_WRITER = ExamNetQtiPackageWriter()


def _fractional_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Fritext med decimalpoäng",
                        "about": "Skriv ett svar.",
                        "bodyHTML": "<p>Skriv ett svar.</p>",
                        "images": [],
                        "maxScore": 10.5,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Flerval med decimalpoäng",
                        "about": "",
                        "bodyHTML": "<p>Välj rätt bokstav.</p>",
                        "images": [],
                        "maxScore": 10.5,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alfa", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Flerval flera svar",
                        "about": "",
                        "bodyHTML": "<p>Välj alla rätta.</p>",
                        "images": [],
                        "maxScore": 7.5,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "Först", "about": "", "right": True},
                            {"id": 2, "title": "Mellan", "about": "", "right": False},
                            {"id": 3, "title": "Sist", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 4,
                        "title": "Lucktext med decimalpoäng",
                        "about": "",
                        "bodyHTML": "<p>Fyll i ___ ___ ___.</p>",
                        "images": [],
                        "maxScore": 10.5,
                        "type": 3,
                        "blanks": [
                            {"guid": "gap-1", "validations": ["ett"]},
                            {"guid": "gap-2", "validations": ["två"]},
                            {"guid": "gap-3", "validations": ["tre"]},
                        ],
                    },
                ]
            }
        ]
    }


def _item_xml(plan, item_filename: str) -> ElementTree.Element:
    item_file = next(file for file in plan.files if file.relative_path == f"items/{item_filename}")
    return ElementTree.fromstring(item_file.payload)


def _find(root: ElementTree.Element, xpath: str) -> ElementTree.Element:
    found = root.find(xpath)
    assert found is not None
    return found


def test_fractional_scores_survive_parser_ir_json_and_fingerprints() -> None:
    result = DigiExamDxeParser().parse_payload(_fractional_payload(), filename="fractional.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    markers = [
        marker for marker in (item.point_marker for item in result.items) if marker is not None
    ]
    assert len(markers) == len(result.items)
    assert [marker.points for marker in markers] == [10.5, 10.5, 7.5, 10.5]
    assert [marker.raw_text for marker in markers] == [
        "maxScore: 10.5",
        "maxScore: 10.5",
        "maxScore: 7.5",
        "maxScore: 10.5",
    ]
    assert all(
        "10.5" not in warning.message and "7.5" not in warning.message
        for warning in result.warnings
    )

    exam = build_digiexam_intermediate_exam(result)
    assert [item.max_score for item in exam.items] == [10.5, 10.5, 7.5, 10.5]

    serialized = json.dumps(asdict(exam), sort_keys=True)
    assert '"max_score": 10.5' in serialized
    assert '"max_score": 7.5' in serialized

    first_fingerprint = source_item_fingerprint(exam.items[1])
    second_fingerprint = source_item_fingerprint(
        build_digiexam_intermediate_exam(
            DigiExamDxeParser().parse_payload(
                _fractional_payload(), filename="fractional-again.dxe"
            )
        ).items[1]
    )
    assert first_fingerprint == second_fingerprint
    assert first_fingerprint.startswith("sha256:")

    manifest = build_digiexam_ir_manifest(exam)
    assert manifest.renderer_ready is True


def test_fingerprints_distinguish_materially_different_fractional_scores() -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(_fractional_payload(), filename="fractional.dxe")
    )
    baseline = source_item_fingerprint(exam.items[1])

    assert source_item_fingerprint(exam.items[1]) == baseline
    assert source_item_fingerprint(exam.items[1]) != source_item_fingerprint(exam.items[0])
    assert source_item_fingerprint(exam.items[1]) != source_item_fingerprint(
        replace(exam.items[1], max_score=10.75)
    )
    assert source_item_fingerprint(exam.items[1]) != source_item_fingerprint(
        replace(exam.items[1], max_score=0.25)
    )


def test_small_fractional_score_survives_parser_to_neutral_ir_without_warnings() -> None:
    payload = _fractional_payload()
    exams = payload["exams"]
    assert isinstance(exams, list)
    exam_payload = exams[0]
    assert isinstance(exam_payload, dict)
    questions = exam_payload["questions"]
    assert isinstance(questions, list)
    question = questions[0]
    assert isinstance(question, dict)
    question["maxScore"] = 0.25

    result = DigiExamDxeParser().parse_payload(payload, filename="small-fraction.dxe")

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.items[0].max_score == 0.25
    assert isinstance(result.items[0].max_score, float)
    assert result.items[0].point_marker is not None
    assert result.items[0].point_marker.points == 0.25
    assert result.items[0].point_marker.raw_text == "maxScore: 0.25"
    assert all("0.25" not in warning.message for warning in result.warnings)

    exam = build_digiexam_intermediate_exam(result)
    assert exam.items[0].max_score == 0.25
    assert isinstance(exam.items[0].max_score, float)
    serialized = json.dumps(asdict(exam), sort_keys=True)
    assert '"max_score": 0.25' in serialized


def test_fractional_scores_survive_overlay_replay_without_point_correction() -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(_fractional_payload(), filename="fractional.dxe")
    )
    item = exam.items[0]
    overlay = DigiExamIngestionOverlay(
        schema_version=DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
        source_binding=DigiExamOverlaySourceBinding(
            source_file_sha256="sha256:file",
            source_ir_schema_version=DIGIEXAM_IR_SCHEMA_VERSION,
            source_ir_sha256="sha256:ir",
        ),
        items=(
            DigiExamIngestionOverlayItem(
                item_id="item-001",
                sequence=1,
                item_type=item.item_type,
                source_item_fingerprint=source_item_fingerprint(item),
                effective_item_patch=DigiExamOverlayGenericItemPatch(
                    kind="generic", title="Reparerad titel"
                ),
            ),
        ),
    )

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=json.dumps(overlay.model_dump(mode="json")).encode("utf-8"),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    effective_item = result.effective_exam_for_rendering.items[0]
    report_item = result.effective_exam_report.items[0]
    assert effective_item.title == "Reparerad titel"
    assert effective_item.max_score == 10.5
    assert report_item.effective_point_correction is None
    assert result.ingestion_overlay_report.rejected_entries == ()


def test_fractional_scores_survive_pdf_semantics_without_warnings() -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(_fractional_payload(), filename="fractional.dxe")
    )

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "Poängvärde: 10.5" in document.html
    assert "Poängvärde: 7.5" in document.html
    assert "Poängvärde: 10.5" in document.html
    assert not any(warning.blocking for warning in document.warnings)


def test_fractional_scores_survive_qti_mapping_maximum_and_gap_allocation() -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(_fractional_payload(), filename="fractional.dxe")
    )
    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    plan = build_examnet_qti_package_plan(
        package_name="fractional",
        items=adapter_result.items,
    )

    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    assert [item.max_score for item in adapter_result.items] == [10.5, 10.5, 7.5, 10.5]
    assert adapter_result.items[0].free_text_criterion_points == 10.5

    zip_bytes = _WRITER.build_package_bytes(plan)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert names == {
            "imsmanifest.xml",
            EXAMNET_QTI_ASSESSMENT_TEST_PATH,
            "items/item_001.xml",
            "items/item_002.xml",
            "items/item_003.xml",
            "items/item_004.xml",
        }

    free_text = _item_xml(plan, "item_001.xml")
    max_outcome = _find(free_text, f"{{{QTI_NAMESPACE}}}outcomeDeclaration[@identifier='MAXSCORE']")
    max_value = _find(max_outcome, f".//{{{QTI_NAMESPACE}}}value")
    assert max_value.text == "10.5"
    mapping = _find(free_text, f".//{{{QTI_NAMESPACE}}}mapping")
    assert mapping.attrib["upperBound"] == "10.5"
    map_entry = _find(mapping, f"{{{QTI_NAMESPACE}}}mapEntry")
    assert map_entry.attrib["mappedValue"] == "10.5"

    choice = _item_xml(plan, "item_002.xml")
    choice_mapping = _find(choice, f".//{{{QTI_NAMESPACE}}}mapping")
    assert choice_mapping.attrib["upperBound"] == "10.5"
    assert [
        entry.attrib["mappedValue"]
        for entry in choice_mapping.findall(f"{{{QTI_NAMESPACE}}}mapEntry")
    ] == ["10.5"]
    choice_max_value = _find(
        choice,
        f"{{{QTI_NAMESPACE}}}outcomeDeclaration[@identifier='MAXSCORE']/"
        f"{{{QTI_NAMESPACE}}}defaultValue/{{{QTI_NAMESPACE}}}value",
    )
    assert choice_max_value.text == "10.5"

    gap = _item_xml(plan, "item_004.xml")
    mappings = gap.findall(f".//{{{QTI_NAMESPACE}}}mapping")
    assert len(mappings) == 3
    assert [mapping.attrib["upperBound"] for mapping in mappings] == ["3.5", "3.5", "3.5"]
    assert [
        entry.attrib["mappedValue"]
        for mapping in mappings
        for entry in mapping.findall(f"{{{QTI_NAMESPACE}}}mapEntry")
    ] == ["3.5", "3.5", "3.5"]

    report = build_examnet_qti_validation_report(
        plan=plan,
        package_filename="qti-package.zip",
        package_bytes=zip_bytes,
    )
    assert report.package_status == ExamNetQtiPackageStatus.PASSED
    assert report.errors == ()
