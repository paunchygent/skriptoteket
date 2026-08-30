"""Source-owned correction state projected from a local exam conversion."""

from __future__ import annotations

import hashlib

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)


def build_correction_source_state(exam: DigiExamIntermediateExam) -> dict[str, JsonValue]:
    """Project the stable producer source state used to bind teacher intents."""

    return {
        "schema_version": "exam_authoring_correction_source_state_v1",
        "source_authoring_schema_version": "exam_authoring_ir_v1",
        "source_state_sha256": "sha256:pending",
        "items": [_source_item(item) for item in exam.items],
    }


def sha256_digest(content: bytes) -> str:
    """Return the digest representation used by correction source bindings."""

    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _source_item(item: DigiExamIrItem) -> dict[str, JsonValue]:
    choice_interactions: list[JsonValue] = []
    if item.item_type in {
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        correct_choice_ids: list[JsonValue] = [
            f"choice-{alternative_id}" for alternative_id in item.answer_key.correct_alternative_ids
        ]
        choices: list[JsonValue] = [
            {
                "choice_id": f"choice-{alternative.id}",
                "source_id": str(alternative.id),
                "order": index,
                "text": alternative.title,
            }
            for index, alternative in enumerate(item.alternatives, start=1)
        ]
        choice_interactions.append(
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": f"choice-{item.item_id}",
                "interaction_kind": item.item_type.value,
                "choices": choices,
                "answer_key": {
                    "correct_choice_ids": correct_choice_ids,
                    "provenance": "source_provided" if correct_choice_ids else "absent",
                },
                "evidence": [],
                "min_correct_choices": 1,
                "max_correct_choices": (
                    1
                    if item.item_type is DigiExamItemType.SINGLE_CHOICE
                    else max(1, len(item.alternatives))
                ),
            }
        )
    gap_interactions: list[JsonValue] = []
    if item.item_type is DigiExamItemType.GAP_FILL:
        accepted_values: list[JsonValue] = [
            {
                "gap_id": answer.guid,
                "value": answer.value,
                "provenance": "source_provided",
                "evidence": [],
            }
            for answer in item.answer_key.correct_gap_answers
        ]
        gaps: list[JsonValue] = [
            {
                "gap_id": gap.guid,
                "display_order": index,
                "evidence": [],
                "prompt_binding": {"kind": "source_locator", "locator": gap.guid},
                "required_for_auto_evaluation": True,
            }
            for index, gap in enumerate(item.gaps, start=1)
        ]
        gap_interactions.append(
            {
                "schema_version": "exam_authoring_ir_v1",
                "interaction_id": f"gap-{item.item_id}",
                "gaps": gaps,
                "answer_key": {
                    "accepted_values": accepted_values,
                    "provenance": "source_provided" if accepted_values else "absent",
                },
                "evidence": [],
                "normalization_profile": "trim_case_sensitive",
            }
        )
    return {
        "item_id": item.item_id,
        "sequence": item.sequence,
        "item_type": item.item_type.value,
        "source_item_fingerprint": source_item_fingerprint(item),
        "title": item.title,
        "prompt_html": item.prompt_html,
        "prompt_lines": list(item.prompt_lines),
        "max_score": item.max_score,
        "choice_interactions": choice_interactions,
        "gap_open_cloze_interactions": gap_interactions,
        "matching_interactions": [],
    }
