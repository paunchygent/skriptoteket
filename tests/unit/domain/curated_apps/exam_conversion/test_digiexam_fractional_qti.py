"""Focused QTI regression tests for fractional DigiExam scores."""

from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE

pytestmark = pytest.mark.unit


def test_positive_fractional_free_text_keeps_criterion_scoring() -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Kort svar",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Förklara kort.",),
        max_score=0.25,
        free_text_criterion_points=0.25,
        expected_lines=8,
    )
    root = ElementTree.fromstring(serialize_qti_assessment_item(item))

    assert item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC
    assert item.max_score == 0.25
    assert item.free_text_criterion_points == 0.25
    mapping = root.find(f".//{{{QTI_NAMESPACE}}}qti-mapping")
    assert mapping is not None
    assert mapping.attrib["upper-bound"] == "0.25"
    entry = mapping.find(f"{{{QTI_NAMESPACE}}}qti-map-entry")
    assert entry is not None
    assert entry.attrib["mapped-value"] == "0.25"


def test_gap_allocation_rounds_equal_share_down_to_whole_cents() -> None:
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
    mappings = root.findall(f".//{{{QTI_NAMESPACE}}}qti-mapping")
    allocations = tuple(mapping.attrib["upper-bound"] for mapping in mappings)

    assert allocations == ("0.04", "0.04", "0.04")
    assert sum(Decimal(value) for value in allocations) == Decimal("0.12")
    max_score = root.find(
        f"{{{QTI_NAMESPACE}}}qti-outcome-declaration[@identifier='MAXSCORE']/"
        f"{{{QTI_NAMESPACE}}}qti-default-value/{{{QTI_NAMESPACE}}}qti-value"
    )
    assert max_score is not None
    assert max_score.text == "0.125"
