"""QTI 3.0 item admissibility and manual follow-up for Exam.net packages.

Purpose:
    Decide whether supplied QTI items can all be represented in a package and
    list the manual follow-up each item needs after import into Exam.net.

Relationships:
    - Consumes `domain.examnet_qti_contracts` items.
    - Used by `domain.examnet_qti_package` to block or plan a package.
"""

from __future__ import annotations

import math
import re

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUp,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiTextEntryGap,
    ExamNetQtiUnsupportedResource,
)

IMAGE_MEDIA_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def manual_follow_ups(items: tuple[ExamNetQtiItem, ...]) -> tuple[ExamNetQtiManualFollowUp, ...]:
    follow_ups: list[ExamNetQtiManualFollowUp] = []
    for item in _leaf_items(items):
        for resource in item.unsupported_resources:
            follow_ups.append(_unsupported_resource_follow_up(item, resource))
        if item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED:
            follow_ups.append(_automatic_evaluation_follow_up(item))
            continue
        if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
            if len(item.correct_choice_identifiers) != 1:
                follow_ups.append(_manual_answer_key_follow_up(item))
        if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
            if not item.correct_choice_identifiers:
                follow_ups.append(_manual_answer_key_follow_up(item))
        if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
            if any(not _accepted_gap_values(gap) for gap in item.text_entry_gaps):
                follow_ups.append(_manual_answer_key_follow_up(item))
    return tuple(follow_ups)


def blocking_errors(items: tuple[ExamNetQtiItem, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    if not items:
        errors.append("QTI package needs at least one item.")
    for item in items:
        if item.children:
            errors.extend(_parent_errors(item))
        else:
            errors.extend(_item_errors(item))
    return tuple(errors)


def _leaf_items(items: tuple[ExamNetQtiItem, ...]) -> tuple[ExamNetQtiItem, ...]:
    return tuple(leaf for item in items for leaf in (item.children or (item,)))


def _parent_errors(parent: ExamNetQtiItem) -> tuple[str, ...]:
    errors: list[str] = []
    if not _SAFE_IDENTIFIER_PATTERN.fullmatch(parent.item_id):
        errors.append(f"Item {parent.item_id} has an unsafe QTI identifier.")
    positioned_picture = any(
        isinstance(segment, ExamNetQtiPromptImage)
        and 0 <= segment.image_index < len(parent.image_resources)
        for paragraph in parent.prompt_paragraphs
        for segment in paragraph.segments
    )
    if not any(line.strip() for line in parent.instruction_lines) and not positioned_picture:
        errors.append(f"Item {parent.item_id} has no instruction text.")
    child_ids = tuple(child.item_id for child in parent.children)
    if len(set(child_ids)) != len(child_ids):
        errors.append(f"Item {parent.item_id} has duplicate child identifiers.")
    for child in parent.children:
        if child.children:
            errors.append(f"Item {child.item_id} cannot nest inside parent {parent.item_id}.")
        else:
            errors.extend(_item_errors(child))
    return tuple(errors)


def _item_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    errors: list[str] = []
    if not _SAFE_IDENTIFIER_PATTERN.fullmatch(item.item_id):
        errors.append(f"Item {item.item_id} has an unsafe QTI identifier.")
    positioned_picture = any(
        isinstance(segment, ExamNetQtiPromptImage)
        and 0 <= segment.image_index < len(item.image_resources)
        for paragraph in item.prompt_paragraphs
        for segment in paragraph.segments
    )
    if not any(line.strip() for line in item.prompt_lines) and not positioned_picture:
        errors.append(f"Item {item.item_id} has no prompt text.")
    if item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC and (
        item.max_score is None or not math.isfinite(item.max_score) or item.max_score < 0
    ):
        errors.append(f"Item {item.item_id} needs a finite non-negative point value.")
    errors.extend(_choice_errors(item))
    errors.extend(_gap_fill_errors(item))
    errors.extend(_inline_choice_errors(item))
    errors.extend(_matching_errors(item))
    errors.extend(_image_errors(item))
    return tuple(errors)


def _choice_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type not in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    }:
        return ()
    errors: list[str] = []
    identifiers = tuple(choice.identifier for choice in item.choices)
    if len(identifiers) < 2:
        errors.append(f"Item {item.item_id} needs at least two choices.")
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"Item {item.item_id} has duplicate choice identifiers.")
    missing = tuple(
        identifier
        for identifier in item.correct_choice_identifiers
        if identifier not in identifiers
    )
    if missing:
        errors.append(f"Item {item.item_id} has answer keys for missing choices.")
    if item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED:
        return tuple(errors)
    if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
        if len(item.correct_choice_identifiers) != 1:
            errors.append(f"Item {item.item_id} needs exactly one correct choice.")
    if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        if not item.correct_choice_identifiers:
            errors.append(f"Item {item.item_id} needs one or more correct choices.")
    return tuple(errors)


def _gap_fill_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type != ExamNetQtiInteractionType.GAP_FILL:
        return ()
    if item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED:
        return ()
    errors: list[str] = []
    if not item.text_entry_gaps:
        errors.append(f"Item {item.item_id} needs one or more text-entry gaps.")
        return tuple(errors)
    identifiers = tuple(gap.response_identifier for gap in item.text_entry_gaps)
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"Item {item.item_id} has duplicate gap response identifiers.")
    unsafe_identifiers = tuple(
        identifier
        for identifier in identifiers
        if not _SAFE_IDENTIFIER_PATTERN.fullmatch(identifier)
    )
    if unsafe_identifiers:
        errors.append(f"Item {item.item_id} has unsafe gap response identifiers.")
    if any(not _accepted_gap_values(gap) for gap in item.text_entry_gaps):
        errors.append(f"Item {item.item_id} needs accepted values for every gap.")
    return tuple(errors)


def _inline_choice_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type is not ExamNetQtiInteractionType.INLINE_CHOICE:
        return ()
    errors: list[str] = []
    gaps = item.inline_choice_gaps
    ids = [gap.response_identifier for gap in gaps]
    if not gaps or len(set(ids)) != len(ids):
        errors.append(f"Item {item.item_id} needs unique inline-choice gap responses.")
    if any(not _SAFE_IDENTIFIER_PATTERN.fullmatch(value) for value in ids):
        errors.append(f"Item {item.item_id} has unsafe gap response identifiers.")
    for gap in gaps:
        options = [option.identifier for option in gap.options]
        if (
            not options
            or len(set(options)) != len(options)
            or gap.correct_option_identifier not in options
            or any(not _SAFE_IDENTIFIER_PATTERN.fullmatch(value) for value in options)
            or any(not option.text.strip() for option in gap.options)
        ):
            errors.append(f"Item {item.item_id} needs a valid option list and one key per gap.")
    placed = [
        segment.gap_index
        for paragraph in item.prompt_paragraphs
        for segment in paragraph.segments
        if isinstance(segment, ExamNetQtiPromptGap)
    ]
    if sorted(placed) != list(range(len(gaps))):
        errors.append(f"Item {item.item_id} must place every inline-choice gap exactly once.")
    return tuple(errors)


def _matching_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type != ExamNetQtiInteractionType.MATCHING:
        return ()
    if not item.match_pairs:
        return (f"Item {item.item_id} needs exact matching pairs.",)
    if item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED:
        return ()
    left = tuple(entry.identifier for entry in item.match_left)
    right = tuple(entry.identifier for entry in item.match_right)
    if not left or not right:
        return (f"Item {item.item_id} needs both matching lists.",)
    if len(set(left + right)) != len(left + right):
        return (f"Item {item.item_id} has duplicate match identifiers.",)
    if any(
        pair.left_identifier not in left or pair.right_identifier not in right
        for pair in item.match_pairs
    ):
        return (f"Item {item.item_id} pairs entries missing from its matching lists.",)
    return ()


def _image_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    errors: list[str] = []
    for image in item.image_resources:
        if image.media_type not in IMAGE_MEDIA_TYPES:
            errors.append(f"Item {item.item_id} has unsupported image type {image.media_type}.")
        if not image.payload:
            errors.append(f"Item {item.item_id} has an empty image payload.")
    return tuple(errors)


def _unsupported_resource_follow_up(
    item: ExamNetQtiItem,
    resource: ExamNetQtiUnsupportedResource,
) -> ExamNetQtiManualFollowUp:
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.UNSUPPORTED_EXAMNET_QTI_RESOURCE,
        message=(
            f"Resursen {resource.label} ({resource.resource_type}) måste läggas till "
            "manuellt efter import i Exam.net."
        ),
        affected_targets=("qti_package",),
    )


def _manual_answer_key_follow_up(item: ExamNetQtiItem) -> ExamNetQtiManualFollowUp:
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED,
        message="Lägg till eller kontrollera facit innan QTI-paketet används i Exam.net.",
        affected_targets=("qti_package",),
    )


def _automatic_evaluation_follow_up(item: ExamNetQtiItem) -> ExamNetQtiManualFollowUp:
    source_type = item.source_item_type or item.interaction_type.value
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.AUTOMATIC_EVALUATION_UNSUPPORTED,
        message=(
            f"Frågan exporteras som manuell QTI utan automatiskt facit "
            f"(ursprunglig frågetyp: {source_type})."
        ),
        affected_targets=("qti_package",),
    )


def _accepted_gap_values(gap: ExamNetQtiTextEntryGap) -> tuple[str, ...]:
    return tuple(value.strip() for value in gap.accepted_values if value.strip())
