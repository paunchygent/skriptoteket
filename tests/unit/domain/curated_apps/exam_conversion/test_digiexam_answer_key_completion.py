"""Tests for machine answer-key completion planning.

Purpose:
    Prove provider-profile construction and enrichment eligibility for unkeyed
    DigiExam items.

Relationships:
    - Exercises `domain.curated_apps.exam_conversion.digiexam_answer_key_completion`
      and the provider profile in `digiexam_answer_key_llm_contracts`.
"""

from __future__ import annotations

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyEnrichmentPlanState,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrManualFollowUpReason,
    build_digiexam_intermediate_exam,
)

pytestmark = pytest.mark.unit


def _exam(questions: list[dict[str, JsonValue]]) -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(
        {"exams": [{"questions": questions}]},
        filename="exam.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _unkeyed_single_choice_question() -> dict[str, JsonValue]:
    return {
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


def _keyed_single_choice_question() -> dict[str, JsonValue]:
    question = _unkeyed_single_choice_question()
    question["alternatives"] = [
        {"id": 1, "title": "Alpha", "about": "", "right": False},
        {"id": 2, "title": "Beta", "about": "", "right": True},
    ]
    return question


def _open_ended_question() -> dict[str, JsonValue]:
    return {
        "id": 2,
        "title": "Essay",
        "about": "",
        "bodyHTML": "<p>Explain.</p>",
        "images": [],
        "maxScore": 4,
        "type": 0,
    }


_PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _asset_bearing_gap_fill_question() -> dict[str, JsonValue]:
    return {
        "id": 2,
        "title": "Gap with image",
        "about": "",
        "bodyHTML": (
            '<p><img data-image-id="0" class="fr-fic fr-dib"/></p><p>Fill in the missing word.</p>'
        ),
        "images": [_PNG_1X1_BASE64],
        "maxScore": 2,
        "type": 3,
        "blanks": [{"guid": "gap-1", "validations": []}],
    }


def test_profile_rejects_output_budget_at_or_above_context_window() -> None:
    with pytest.raises(ValueError):
        StructuredLLMProviderProfile(
            provider_id="openai-gpt-5.6-luna",
            model="gpt-5.6-luna",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=True,
            context_window_tokens=4_096,
            max_output_tokens=4_096,
        )


def test_unkeyed_choice_exam_is_eligible_for_enrichment() -> None:
    plan = plan_answer_key_enrichment(_exam([_unkeyed_single_choice_question()]))

    assert plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE
    assert tuple(item.item_id for item in plan.unkeyed_items) == ("item-001",)


def test_source_keyed_exam_needs_no_enrichment() -> None:
    plan = plan_answer_key_enrichment(_exam([_keyed_single_choice_question()]))

    assert plan.state is AnswerKeyEnrichmentPlanState.NOT_NEEDED
    assert plan.unkeyed_items == ()


def test_asset_bearing_item_does_not_block_supported_unkeyed_items() -> None:
    exam = _exam([_unkeyed_single_choice_question(), _asset_bearing_gap_fill_question()])

    plan = plan_answer_key_enrichment(exam)

    assert plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE
    assert tuple(item.item_id for item in plan.unkeyed_items) == ("item-001",)
    assert {(follow_up.item_id, follow_up.reason) for follow_up in exam.manual_follow_ups} == {
        ("item-001", DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED),
        ("item-002", DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED),
    }


def test_manual_marking_items_do_not_block_supported_unkeyed_items() -> None:
    exam = _exam([_unkeyed_single_choice_question(), _open_ended_question()])

    plan = plan_answer_key_enrichment(exam)

    assert plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE
    assert tuple(item.item_id for item in plan.unkeyed_items) == ("item-001",)
    assert {(follow_up.item_id, follow_up.reason) for follow_up in exam.manual_follow_ups} == {
        ("item-001", DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED),
        ("item-002", DigiExamIrManualFollowUpReason.MANUAL_MARKING_REQUIRED),
    }
