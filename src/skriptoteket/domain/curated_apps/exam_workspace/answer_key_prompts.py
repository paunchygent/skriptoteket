"""Model-facing prompt payloads for native exam workspace answer-key proposals.

Purpose:
    Build item-local structured-output requests from neutral
    ``AnswerKeyItemView`` projections, reusing the DigiExam answer-key
    completion line verbatim where it is shared: the same system prompts,
    prompt-template versions, and structured output specs. Only the user
    payload assembly is view-based; the decision schemas are not forked.

Relationships:
    - Consumed by the workspace branch of
      ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
    - Reuses ``digiexam_answer_key_prompts`` and
      ``digiexam_answer_key_completion`` exports; gap numbering mirrors the
      ``<span dx-wg-id>`` numbering those modules derive from prompt HTML.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    choice_decision_output_spec,
    numbered_gap_fill_output_spec,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredOutputSpec,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
    _choice_answer_shape,
    _choice_user_instruction,
    system_prompt_for_answer_key_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import DigiExamItemType
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyItemView,
    AnswerKeyViewKind,
)

_ITEM_TYPE_BY_VIEW_KIND: dict[AnswerKeyViewKind, DigiExamItemType] = {
    AnswerKeyViewKind.CHOICE: DigiExamItemType.SINGLE_CHOICE,
    AnswerKeyViewKind.MULTI: DigiExamItemType.MULTIPLE_RESPONSE,
    AnswerKeyViewKind.GAP_FILL: DigiExamItemType.GAP_FILL,
}


@dataclass(frozen=True)
class WorkspaceAnswerKeyCandidatePlan:
    """One item-local provider interaction for a workspace key proposal."""

    view: AnswerKeyItemView
    request: StructuredLLMRequest


def prompt_item_type_for_view(view: AnswerKeyItemView) -> DigiExamItemType:
    """Return the shared prompt item type one view maps onto."""

    return _ITEM_TYPE_BY_VIEW_KIND[view.kind]


def choice_answer_key_model_payload_from_view(view: AnswerKeyItemView) -> dict[str, JsonValue]:
    """Build the model-facing payload for a choice-style workspace item."""

    item_type = prompt_item_type_for_view(view)
    maximum_answers = len(view.choices) if item_type is DigiExamItemType.MULTIPLE_RESPONSE else 1
    return {
        "task": {
            "name": "select_teacher_intended_choice_answer_key",
            "item_type": item_type.value,
            "instruction": _choice_user_instruction(item_type),
        },
        "item": {
            "item_id": view.item_id,
            "title": view.title,
            "stem": view.stem_text,
        },
        "choices": [
            {
                "choice_value": str(choice_id),
                "alternative_id": choice_id,
                "text": text,
            }
            for choice_id, text in view.choices
        ],
        "selection_rules": {"min_choices": 1, "max_choices": maximum_answers},
        "output": {
            "provider_output_mode": "json_schema",
            "answer_shape": _choice_answer_shape(item_type),
        },
    }


def gap_fill_answer_key_model_payload_from_view(view: AnswerKeyItemView) -> dict[str, JsonValue]:
    """Build the model-facing payload for a gap-fill workspace item."""

    gap_entries: list[JsonValue] = [{"gap_number": index} for index in range(1, view.gap_count + 1)]
    return {
        "task": {
            "name": "complete_teacher_intended_gap_fill_answer_key",
            "item_type": DigiExamItemType.GAP_FILL.value,
            "instruction": (
                "Read the cloze item as a teacher-authored exam question. "
                "Each [number] marker is one blank. Choose the "
                "teacher-intended accepted value for every numbered blank."
            ),
        },
        "item": {
            "item_id": view.item_id,
            "title": view.title,
            "cloze_text": view.cloze_text,
        },
        "gaps": gap_entries,
        "output": {
            "provider_output_mode": "json_schema",
            "json_shape": (
                'Return one JSON object. Use string keys "1" through '
                f'"{len(gap_entries)}" for the numbered blanks.'
            ),
            "accepted_values": (
                "Each numbered key value must be exactly one short answer "
                "string matching what the student is expected to place in the "
                "blank. When a visible word bank or candidate list provides the "
                "intended answers, use only the exact candidate value from that "
                "bank or list. If candidates are labeled with short labels such "
                "as A, B, C, D, E, 1, 2, 3, or similar and the longer text "
                "explains each label, return only the label, not the explanation. "
                "If the question says to write the correct number, letter, or "
                "other label type, use that requested label type and do not copy "
                "the surrounding row label for the blank. "
                "Use a full precise term only when no word bank, candidate list, "
                "or candidate label is visible."
            ),
        },
    }


def plan_workspace_answer_key_candidates(
    *,
    job_id: str,
    views: tuple[AnswerKeyItemView, ...],
    profile: StructuredLLMProviderProfile,
) -> tuple[WorkspaceAnswerKeyCandidatePlan, ...]:
    """Build one provider request per unkeyed workspace item view."""

    plans: list[WorkspaceAnswerKeyCandidatePlan] = []
    for view in views:
        if view.kind is AnswerKeyViewKind.GAP_FILL:
            prompt_template_version = GAP_FILL_PROMPT_TEMPLATE_VERSION
            output_spec = numbered_gap_fill_output_spec(view.gap_count)
            user_payload = gap_fill_answer_key_model_payload_from_view(view)
        else:
            prompt_template_version = CHOICE_PROMPT_TEMPLATE_VERSION
            output_spec = choice_decision_output_spec()
            user_payload = choice_answer_key_model_payload_from_view(view)
        plans.append(
            WorkspaceAnswerKeyCandidatePlan(
                view=view,
                request=_request(
                    job_id=job_id,
                    view=view,
                    prompt_template_version=prompt_template_version,
                    output_spec=output_spec,
                    user_payload=user_payload,
                    profile=profile,
                ),
            )
        )
    return tuple(plans)


def _request(
    *,
    job_id: str,
    view: AnswerKeyItemView,
    prompt_template_version: str,
    output_spec: StructuredOutputSpec,
    user_payload: dict[str, JsonValue],
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMRequest:
    user_payload_text = json.dumps(
        user_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    item_type = prompt_item_type_for_view(view)
    system_prompt = system_prompt_for_answer_key_item(item_type)
    return StructuredLLMRequest(
        job_id=job_id,
        item_id=view.item_id,
        item_type=item_type.value,
        prompt_template_version=prompt_template_version,
        system_prompt=system_prompt,
        user_payload=user_payload_text,
        output_spec=output_spec,
        estimated_input_tokens=(
            estimate_prompt_tokens(system_prompt) + estimate_prompt_tokens(user_payload_text)
        ),
        max_output_tokens=profile.max_output_tokens,
    )
