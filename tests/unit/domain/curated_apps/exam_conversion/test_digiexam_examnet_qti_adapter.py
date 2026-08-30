"""Regression tests for zero-point DigiExam free-text QTI adaptation.

Purpose:
    Prove that open-ended DigiExam questions without positive points remain
    native Exam.net manual text interactions instead of acquiring a score.

Relationships:
    - Exercises the DigiExam parser and intermediate representation boundary.
    - Verifies the adapter output through the Exam.net QTI package planner.
"""

from __future__ import annotations

from dataclasses import replace
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("max_score", (0, None))
def test_zero_or_absent_open_ended_points_stay_manual_native_text(
    max_score: int | None,
) -> None:
    exam = _open_ended_exam(max_score=0)
    if max_score is None:
        exam = replace(exam, items=(replace(exam.items[0], max_score=None),))

    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    adapted_item = adapter_result.items[0]
    plan = build_examnet_qti_package_plan(
        package_name="zero-or-absent-open-ended",
        items=adapter_result.items,
    )
    item_xml = _planned_item_xml(plan)

    assert adapted_item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT
    assert adapted_item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED
    assert adapted_item.max_score == max_score
    assert adapted_item.free_text_criterion_points is None
    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    assert item_xml.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item_xml.find(f".//{{{QTI_NAMESPACE}}}mapping") is None
    assert item_xml.find(f"{{{QTI_NAMESPACE}}}responseProcessing") is None


def test_positive_open_ended_points_keep_criterion_scoring() -> None:
    adapter_result = build_examnet_qti_items_from_digiexam_ir(_open_ended_exam(max_score=3))
    adapted_item = adapter_result.items[0]
    plan = build_examnet_qti_package_plan(
        package_name="positive-open-ended",
        items=adapter_result.items,
    )
    item_xml = _planned_item_xml(plan)

    assert adapted_item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT
    assert adapted_item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC
    assert adapted_item.max_score == 3
    assert adapted_item.free_text_criterion_points == 3
    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    assert item_xml.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item_xml.find(f".//{{{QTI_NAMESPACE}}}mapping") is not None
    assert item_xml.find(f"{{{QTI_NAMESPACE}}}responseProcessing") is not None


def _open_ended_exam(*, max_score: int) -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Short explanation",
                            "about": "",
                            "bodyHTML": "<p>Explain your reasoning.</p>",
                            "images": [],
                            "maxScore": max_score,
                            "type": 0,
                        }
                    ]
                }
            ]
        },
        filename="open-ended-points.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _planned_item_xml(plan: ExamNetQtiPackagePlan) -> ElementTree.Element:
    item_files = tuple(file for file in plan.files if file.relative_path.startswith("items/"))
    assert len(item_files) == 1
    return ElementTree.fromstring(item_files[0].payload)
