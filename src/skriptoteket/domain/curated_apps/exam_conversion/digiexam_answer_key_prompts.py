"""Shared DigiExam answer-key prompt line for workspace payloads.

Purpose:
    Provide the shared system prompts, prompt-template versions, and
    choice/gap-fill guidance text that the native workspace answer-key
    prompt builders reuse verbatim.

Relationships:
    - Consumed by the workspace answer-key prompts before provider
      request construction.
    - Gap-fill labels bind to the numbered ``[n]`` markers in workspace
      cloze text.
"""

from __future__ import annotations

import re

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import DigiExamItemType

CHOICE_PROMPT_TEMPLATE_VERSION = "digiexam_choice_answer_key_prompt_v1"
GAP_FILL_PROMPT_TEMPLATE_VERSION = "digiexam_gap_fill_answer_key_prompt_v2"

BASE_ANSWER_KEY_SYSTEM_PROMPT = (
    "You propose only structured answer-key candidates for one exam item. "
    "Return no rationale, confidence, prose, or source/provenance claims."
)

CHOICE_ANSWER_KEY_SYSTEM_PROMPT = (
    f"{BASE_ANSWER_KEY_SYSTEM_PROMPT} For choice items, infer the "
    "teacher-intended correct alternative id or ids from the visible item text "
    "and alternatives. Evaluate each alternative independently against the item "
    "stem. Only select an alternative if you can positively confirm it is correct. "
    "Do not select alternatives that are merely plausible or related."
)

GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT = (
    f"{BASE_ANSWER_KEY_SYSTEM_PROMPT} For gap-fill items, infer the "
    "teacher-intended accepted value for each visible gap marker from the "
    "surrounding cloze text and any visible word bank or candidate list. "
    "Return the exact value a student is expected to put in the blank. When "
    "a candidate is identified by a short label and longer text, return only "
    "the label. If the question explicitly says to write a number, letter, "
    "or other label type, follow that instruction even when both sides are "
    "labeled. Do not paraphrase, substitute synonyms, or expand labels."
)

_GAP_MARKER = re.compile(r"\[(\d+)\]")

_CHOICE_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)


def system_prompt_for_answer_key_item(item_type: DigiExamItemType) -> str:
    """Return type-specific system guidance for one answer-key candidate."""

    if item_type in _CHOICE_ITEM_TYPES:
        return CHOICE_ANSWER_KEY_SYSTEM_PROMPT
    if item_type == DigiExamItemType.GAP_FILL:
        return GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    return BASE_ANSWER_KEY_SYSTEM_PROMPT


def numbered_gap_labels(cloze_text: str, gap_count: int) -> tuple[str, ...]:
    """Return the text printed before each numbered ``[n]`` gap marker.

    The label for gap ``n`` is the text since the previous marker or the start
    of its line, whichever is later, stripped and with one trailing colon
    removed. A marker with nothing before it, or a number whose marker does not
    appear, gets an empty label.
    """

    labels: dict[int, str] = {}
    for line in cloze_text.splitlines():
        label_start = 0
        for marker in _GAP_MARKER.finditer(line):
            number = int(marker.group(1))
            if number not in labels:
                labels[number] = _gap_label(line[label_start : marker.start()])
            label_start = marker.end()
    return tuple(labels.get(number, "") for number in range(1, gap_count + 1))


def _gap_label(text: str) -> str:
    return text.strip().removesuffix(":").strip()


def _choice_user_instruction(item_type: DigiExamItemType) -> str:
    if item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return (
            "Read the item as a teacher-authored exam question. This item type "
            "allows one or more correct answers. Evaluate each alternative "
            "independently against the item stem and include only those you can "
            "confirm as correct. Use only the provided choice_value values."
        )
    return (
        "Read the item as a teacher-authored exam question. This item type has "
        "exactly one correct answer. Select the single teacher-intended correct "
        "choice from the listed choices. Use only the provided choice_value values."
    )


def _choice_answer_shape(item_type: DigiExamItemType) -> str:
    if item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return (
            "Return a JSON object with a correct_alternative_ids array. "
            "The array must contain one or more integer ids, in ascending "
            "order, using only the listed alternative_id values."
        )
    return (
        "Return a JSON object with a correct_alternative_ids array "
        "containing exactly one integer id, using only the listed "
        "alternative_id values."
    )
