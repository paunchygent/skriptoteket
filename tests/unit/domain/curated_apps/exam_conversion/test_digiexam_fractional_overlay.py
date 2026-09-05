"""Fractional score regression tests for DigiExam ingestion overlays."""

from __future__ import annotations

import json

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)

pytestmark = pytest.mark.unit


def _source_exam():
    parsed = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Single without key",
                            "about": "",
                            "bodyHTML": "<p>Choose the Greek letter.</p>",
                            "images": [],
                            "maxScore": 2,
                            "type": 1,
                            "alternatives": [
                                {"id": 1, "title": "Alpha", "about": "", "right": False},
                                {"id": 2, "title": "Beta", "about": "", "right": False},
                            ],
                        }
                    ]
                }
            ]
        },
        filename="exam.dxe",
    )
    return build_digiexam_intermediate_exam(parsed)


def _overlay_bytes(source_fingerprint: str, *, max_score: object) -> bytes:
    return json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": "sha256:file",
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
                "source_ir_sha256": "sha256:ir",
            },
            "items": [
                {
                    "item_id": "item-001",
                    "sequence": 1,
                    "item_type": "single_choice",
                    "source_item_fingerprint": source_fingerprint,
                    "point_correction": {
                        "kind": "item_points",
                        "max_score": max_score,
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


@pytest.mark.parametrize("fractional_max_score", [10.5, 0.25])
def test_fractional_point_correction_preserves_score_through_effective_exam(
    fractional_max_score: float,
) -> None:
    exam = _source_exam()
    item_fingerprint = source_item_fingerprint(exam.items[0])

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_overlay_bytes(item_fingerprint, max_score=fractional_max_score),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    effective_item = result.effective_exam_for_rendering.items[0]
    report_item = result.effective_exam_report.items[0]
    assert exam.items[0].max_score == 2
    assert effective_item.max_score == fractional_max_score
    assert source_item_fingerprint(exam.items[0]) == item_fingerprint
    assert result.renderer_input_changed is True
    assert result.ingestion_overlay_report.rejected_entries == ()
    assert report_item.effective_point_correction is not None
    assert report_item.effective_point_correction.effective_max_score == fractional_max_score


@pytest.mark.parametrize("invalid_max_score", ["10.5", 0, -1, float("inf")])
def test_point_correction_keeps_rejecting_malformed_scores(invalid_max_score: object) -> None:
    exam = _source_exam()

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_overlay_bytes(
                source_item_fingerprint(exam.items[0]),
                max_score=invalid_max_score,
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_invalid"
