"""Focused QTI regression tests for fractional DigiExam scores."""

from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    QTI_NAMESPACE,
    serialize_qti_assessment_item,
)

pytestmark = pytest.mark.unit


def test_positive_fractional_free_text_keeps_criterion_scoring() -> None:
    result = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Kort svar",
                            "about": "",
                            "bodyHTML": "<p>Förklara kort.</p>",
                            "images": [],
                            "maxScore": 0.25,
                            "type": 0,
                        }
                    ]
                }
            ]
        },
        filename="fractional-free-text.dxe",
    )
    exam = build_digiexam_intermediate_exam(result)

    item = build_examnet_qti_items_from_digiexam_ir(exam).items[0]
    root = ElementTree.fromstring(serialize_qti_assessment_item(item))

    assert item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC
    assert item.max_score == 0.25
    assert item.free_text_criterion_points == 0.25
    mapping = root.find(f".//{{{QTI_NAMESPACE}}}mapping")
    assert mapping is not None
    assert mapping.attrib["upperBound"] == "0.25"
    entry = mapping.find(f"{{{QTI_NAMESPACE}}}mapEntry")
    assert entry is not None
    assert entry.attrib["mappedValue"] == "0.25"


def test_gap_allocation_preserves_fraction_beyond_whole_cents() -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Tre luckor",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("___ ___ ___",),
        max_score=0.125,
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_{index}",
                label=f"Lucka {index}",
                accepted_values=(f"svar {index}",),
            )
            for index in range(1, 4)
        ),
    )

    root = ElementTree.fromstring(serialize_qti_assessment_item(item))
    mappings = root.findall(f".//{{{QTI_NAMESPACE}}}mapping")
    allocations = tuple(mapping.attrib["upperBound"] for mapping in mappings)

    assert allocations == ("0.042", "0.042", "0.041")
    assert sum(Decimal(value) for value in allocations) == Decimal("0.125")
    max_score = root.find(
        f"{{{QTI_NAMESPACE}}}outcomeDeclaration[@identifier='MAXSCORE']/"
        f"{{{QTI_NAMESPACE}}}defaultValue/{{{QTI_NAMESPACE}}}value"
    )
    assert max_score is not None
    assert max_score.text == "0.125"
