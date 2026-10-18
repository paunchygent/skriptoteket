"""DigiExam machine answer-key completion planning.

Purpose:
    Decide whether unkeyed DigiExam items need machine answer-key enrichment
    and define the structured-output specs for choice and gap-fill decisions.

Relationships:
    - Ported behavior from sir-convert-a-lot `76983339` candidate planning and
      payload validation, trimmed to the JSON-Schema Responses lane.
    - Consumes `digiexam_answer_key_llm_contracts`; used by the public
      converter local execution and the exam workspace answer-key prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredOutputSpec,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
    DigiExamWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
    DigiExamIrManualFollowUpReason,
)

CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION = "digiexam_choice_answer_key_decision_v1"
GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION = "digiexam_gap_fill_answer_key_decision_v1"

_CHOICE_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
_SOURCE_REPAIR_WARNING_CODES = frozenset(
    {
        DigiExamWarningCode.MISSING_PROMPT_IMAGE,
        DigiExamWarningCode.MISSING_QUESTION_TITLE,
    }
)


class AnswerKeyEnrichmentPlanState(StrEnum):
    """Enqueue-time decision for one parsed in-process conversion source."""

    NOT_NEEDED = "not_needed"
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class AnswerKeyEnrichmentPlan:
    """Unkeyed-item enrichment decision for one parsed exam."""

    state: AnswerKeyEnrichmentPlanState
    unkeyed_items: tuple[DigiExamIrItem, ...]


def choice_decision_output_spec() -> StructuredOutputSpec:
    """Return the provider-neutral choice decision JSON Schema spec."""

    return StructuredOutputSpec(
        schema_name=CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["correct_alternative_ids"],
        },
    )


def numbered_gap_fill_output_spec(gap_count: int) -> StructuredOutputSpec:
    """Return a numbered gap-fill facit JSON Schema spec."""

    if gap_count <= 0:
        raise ValueError("Numbered gap-fill output spec requires at least one gap.")
    answer_keys = tuple(str(index) for index in range(1, gap_count + 1))
    properties: dict[str, JsonValue] = {key: {"type": "string"} for key in answer_keys}
    return StructuredOutputSpec(
        schema_name=GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": [*answer_keys],
        },
    )


def plan_answer_key_enrichment(exam: DigiExamIntermediateExam) -> AnswerKeyEnrichmentPlan:
    """Decide whether machine proposals can complete this parsed exam.

    Eligible machine-marked items receive text-only structured proposals.
    Unsupported unkeyed items stay untouched in the source IR for manual
    review. Open-ended items may remain on the manual marking path; exam-level
    blockers prevent enrichment until their existing manual follow-up is resolved.
    """

    if not any(
        follow_up.reason == DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
        for follow_up in exam.manual_follow_ups
    ):
        return AnswerKeyEnrichmentPlan(
            state=AnswerKeyEnrichmentPlanState.NOT_NEEDED,
            unkeyed_items=(),
        )
    enrichable_items = tuple(
        item
        for item in exam.items
        if item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT
        and item_is_enrichable(item)
    )
    other_blockers = tuple(
        follow_up
        for follow_up in exam.manual_follow_ups
        if follow_up.reason
        not in {
            DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED,
            DigiExamIrManualFollowUpReason.MANUAL_MARKING_REQUIRED,
        }
    )
    if other_blockers:
        return AnswerKeyEnrichmentPlan(
            state=AnswerKeyEnrichmentPlanState.BLOCKED,
            unkeyed_items=enrichable_items,
        )
    if not enrichable_items:
        return AnswerKeyEnrichmentPlan(
            state=AnswerKeyEnrichmentPlanState.BLOCKED,
            unkeyed_items=(),
        )
    return AnswerKeyEnrichmentPlan(
        state=AnswerKeyEnrichmentPlanState.ELIGIBLE,
        unkeyed_items=enrichable_items,
    )


def item_is_enrichable(item: DigiExamIrItem) -> bool:
    """Return whether one unkeyed item supports a text-only machine proposal."""

    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return False
    if any(
        warning.blocking or warning.code in _SOURCE_REPAIR_WARNING_CODES
        for warning in item.warnings
    ):
        return False
    if item.embedded_assets or item.embedded_asset_references:
        return False
    if item.item_type in _CHOICE_ITEM_TYPES:
        ids = tuple(alternative.id for alternative in item.alternatives)
        return bool(ids) and len(set(ids)) == len(ids)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return bool(item.gaps) and all(gap.guid.strip() for gap in item.gaps)
    return False
