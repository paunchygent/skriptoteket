"""DigiExam machine answer-key completion planning and proposal assembly.

Purpose:
    Plan item-local structured-output requests for unkeyed DigiExam items,
    validate provider decisions, and assemble the machine-proposed ingestion
    overlay that carries proposals into the existing conversion flow.

Relationships:
    - Ported behavior from sir-convert-a-lot `76983339` candidate planning and
      payload validation, trimmed to the JSON-Schema Responses lane.
    - Consumes `digiexam_answer_key_llm_contracts` and
      `digiexam_answer_key_prompts`; emits `digiexam_ingestion_overlay_contracts`
      documents applied by `digiexam_ingestion_overlay`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredOutputSpec,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    choice_answer_key_model_payload,
    gap_fill_answer_key_model_payload,
    system_prompt_for_answer_key_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlay,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayChoiceManualAnswerKey,
    DigiExamOverlayGapAnswer,
    DigiExamOverlayGapFillManualAnswerKey,
    DigiExamOverlayManualAnswerKey,
    DigiExamOverlaySourceBinding,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    DigiExamIntermediateExam,
    DigiExamIrItem,
    DigiExamIrManualFollowUpReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
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


@dataclass(frozen=True)
class AnswerKeyCandidatePlan:
    """One item-local provider interaction for a machine key proposal."""

    item: DigiExamIrItem
    request: StructuredLLMRequest


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

    ELIGIBLE requires that every unkeyed machine-marked item can carry one
    text-only structured proposal. Open-ended items may remain on the manual
    marking path while supported unkeyed items are enriched; other blockers
    keep the exam on the unchanged ST-SKRIPT-39-01 manual-follow-up path.
    """

    unkeyed_items = tuple(
        item
        for item in exam.items
        if item.answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT
    )
    if not any(
        follow_up.reason == DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
        for follow_up in exam.manual_follow_ups
    ):
        return AnswerKeyEnrichmentPlan(
            state=AnswerKeyEnrichmentPlanState.NOT_NEEDED,
            unkeyed_items=(),
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
            unkeyed_items=unkeyed_items,
        )
    enrichable_items = tuple(item for item in unkeyed_items if item_is_enrichable(item))
    if len(enrichable_items) != len(unkeyed_items) or not enrichable_items:
        return AnswerKeyEnrichmentPlan(
            state=AnswerKeyEnrichmentPlanState.BLOCKED,
            unkeyed_items=unkeyed_items,
        )
    return AnswerKeyEnrichmentPlan(
        state=AnswerKeyEnrichmentPlanState.ELIGIBLE,
        unkeyed_items=enrichable_items,
    )


def item_is_enrichable(item: DigiExamIrItem) -> bool:
    """Return whether one unkeyed item supports a text-only machine proposal."""

    if item.answer_key.provenance != DigiExamAnswerKeyProvenance.ABSENT:
        return False
    if any(warning.blocking for warning in item.warnings):
        return False
    if item.embedded_assets or item.embedded_asset_references:
        return False
    if item.item_type in _CHOICE_ITEM_TYPES:
        ids = tuple(alternative.id for alternative in item.alternatives)
        return bool(ids) and len(set(ids)) == len(ids)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return bool(item.gaps) and all(gap.guid.strip() for gap in item.gaps)
    return False


def plan_answer_key_candidates(
    *,
    job_id: str,
    items: tuple[DigiExamIrItem, ...],
    profile: StructuredLLMProviderProfile,
) -> tuple[AnswerKeyCandidatePlan, ...]:
    """Build one provider request per enrichable unkeyed item."""

    plans: list[AnswerKeyCandidatePlan] = []
    for item in items:
        if not item_is_enrichable(item):
            raise ValueError(f"Item {item.item_id} is not enrichable.")
        if item.item_type in _CHOICE_ITEM_TYPES:
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=CHOICE_PROMPT_TEMPLATE_VERSION,
                output_spec=choice_decision_output_spec(),
                user_payload=choice_answer_key_model_payload(item),
                profile=profile,
            )
        else:
            request = _request(
                job_id=job_id,
                item=item,
                prompt_template_version=GAP_FILL_PROMPT_TEMPLATE_VERSION,
                output_spec=numbered_gap_fill_output_spec(len(item.gaps)),
                user_payload=gap_fill_answer_key_model_payload(item),
                profile=profile,
            )
        plans.append(AnswerKeyCandidatePlan(item=item, request=request))
    return tuple(plans)


def manual_answer_key_from_model_content(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> DigiExamOverlayManualAnswerKey | None:
    """Return a validated overlay manual key from one provider decision."""

    if item.item_type in _CHOICE_ITEM_TYPES:
        return _validated_choice_key(item=item, content=content)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return _validated_gap_key(item=item, content=content)
    return None


def build_machine_proposed_overlay(
    *,
    source_file_sha256: str,
    source_ir_sha256: str,
    proposals: tuple[tuple[DigiExamIrItem, DigiExamOverlayManualAnswerKey], ...],
) -> DigiExamIngestionOverlay:
    """Assemble the machine-proposed overlay document for validated proposals."""

    if not proposals:
        raise ValueError("A machine-proposed overlay requires at least one proposal.")
    return DigiExamIngestionOverlay(
        schema_version=DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
        source_binding=DigiExamOverlaySourceBinding(
            source_file_sha256=source_file_sha256,
            source_ir_schema_version=DIGIEXAM_IR_SCHEMA_VERSION,
            source_ir_sha256=source_ir_sha256,
        ),
        items=tuple(
            DigiExamIngestionOverlayItem(
                item_id=item.item_id,
                sequence=item.sequence,
                item_type=item.item_type,
                source_item_fingerprint=source_item_fingerprint(item),
                manual_answer_key=key,
            )
            for item, key in proposals
        ),
    )


def overlay_json_bytes(overlay: DigiExamIngestionOverlay) -> bytes:
    """Serialize one overlay document to canonical JSON bytes."""

    payload = overlay.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _request(
    *,
    job_id: str,
    item: DigiExamIrItem,
    prompt_template_version: str,
    output_spec: StructuredOutputSpec,
    user_payload: dict[str, JsonValue],
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMRequest:
    user_payload_text = json.dumps(
        user_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    system_prompt = system_prompt_for_answer_key_item(item.item_type)
    return StructuredLLMRequest(
        job_id=job_id,
        item_id=item.item_id,
        item_type=item.item_type.value,
        prompt_template_version=prompt_template_version,
        system_prompt=system_prompt,
        user_payload=user_payload_text,
        output_spec=output_spec,
        estimated_input_tokens=(
            estimate_prompt_tokens(system_prompt) + estimate_prompt_tokens(user_payload_text)
        ),
        max_output_tokens=profile.max_output_tokens,
    )


def _validated_choice_key(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> DigiExamOverlayChoiceManualAnswerKey | None:
    ids = _int_tuple(content.get("correct_alternative_ids"))
    if not ids or len(set(ids)) != len(ids):
        return None
    valid_ids = {alternative.id for alternative in item.alternatives}
    if any(alternative_id not in valid_ids for alternative_id in ids):
        return None
    if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE and len(ids) != 1:
        return None
    return DigiExamOverlayChoiceManualAnswerKey(kind="choice", correct_alternative_ids=ids)


def _validated_gap_key(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> DigiExamOverlayGapFillManualAnswerKey | None:
    gap_answers: list[DigiExamOverlayGapAnswer] = []
    for index, gap in enumerate(item.gaps, start=1):
        value = content.get(str(index))
        if not isinstance(value, str) or not value.strip():
            return None
        gap_answers.append(
            DigiExamOverlayGapAnswer(gap_id=gap.guid, accepted_values=(value.strip(),))
        )
    if len(gap_answers) != len(item.gaps):
        return None
    return DigiExamOverlayGapFillManualAnswerKey(kind="gap_fill", gap_answers=tuple(gap_answers))


def _int_tuple(value: JsonValue | None) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    integers: list[int] = []
    for entry in value:
        if not isinstance(entry, int) or isinstance(entry, bool):
            return ()
        integers.append(entry)
    return tuple(integers)
