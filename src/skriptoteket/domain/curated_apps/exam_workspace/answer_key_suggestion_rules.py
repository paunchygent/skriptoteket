"""Rules for when an AI suggestion kept on a question becomes its answer key.

Purpose:
    Decide what an arriving AI answer-key suggestion does to its question
    (TASK-SKRIPT-39-04-07 T5 as amended by P12 and P13). The suggestion is
    always kept on the question. It also becomes the key only when two
    conditions hold. First, it must fit the question: it would be a valid
    key for the question's current kind and ids. Second, the question must
    have no key, or an unreviewed ``machine_proposed`` key equal, as a whole
    key, to its previous suggestion. This module also restores a kept
    suggestion as the key (T6), which needs only the fit.

Relationships:
    - Reads the item model in
      ``domain.curated_apps.exam_workspace.native_exam_document``, whose
      validation is the one definition of a valid saved key.
    - Mirrored by the editor in
      ``frontend/.../exam-workspace/examWorkspaceItemEdits.ts``.
"""

from __future__ import annotations

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
    NativeExamItem,
    NativeItemReviewState,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON = "machine_proposed_answer_key"


def _key_matches_suggestion(item: NativeExamItem, suggestion: NativeAnswerKeySuggestion) -> bool:
    """Whether the item's current key is this suggestion's whole key, in any order.

    Choice ids, match pairs and the map from each gap with accepted values
    to its set of values must each be equal as sets. A historical id the
    suggestion still names, or any other extra or missing entry, makes them
    unequal.
    """

    key_gaps = {
        gap.gap_id: frozenset(gap.accepted_values) for gap in item.gaps if gap.accepted_values
    }
    suggested_gaps = {
        entry.gap_id: frozenset(entry.accepted_values) for entry in suggestion.gap_accepted_values
    }
    return (
        set(item.answer_key.correct_choice_ids) == set(suggestion.correct_choice_ids)
        and set(item.answer_key.match_pairs) == set(suggestion.match_pairs)
        and key_gaps == suggested_gaps
    )


def _follows_arrivals(item: NativeExamItem) -> bool:
    """Whether the item's key gives way to an arriving suggestion (T5, P12).

    Only where the question has no key, or its key is an unreviewed
    ``machine_proposed`` key equal to the previous suggestion. A source,
    teacher or reviewed key stays, even when it equals the previous
    suggestion.
    """

    origin = item.answer_key.origin
    if origin is NativeAnswerKeyOrigin.ABSENT:
        return True
    previous = item.ai_suggestion
    return (
        origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
        and item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and previous is not None
        and _key_matches_suggestion(item, previous)
    )


def _item_with_suggestion_key(
    item: NativeExamItem, suggestion: NativeAnswerKeySuggestion
) -> NativeExamItem | None:
    """The item with the suggestion as its MACHINE_PROPOSED key, review required.

    Returns ``None`` when the suggestion does not fit the question (P13):
    a gap suggestion that does not name exactly the question's gaps, or a
    key the item's own validation refuses, such as one naming a choice or
    match entry the question no longer declares.
    """

    payload = item.model_dump()
    payload["ai_suggestion"] = suggestion.model_dump()
    reasons = tuple(payload["review"]["reasons"])
    if MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON not in reasons:
        reasons = (*reasons, MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON)
    payload["review"] = {
        **payload["review"],
        "state": NativeItemReviewState.REVIEW_REQUIRED,
        "reasons": reasons,
    }
    values_by_gap = {
        entry.gap_id: entry.accepted_values for entry in suggestion.gap_accepted_values
    }
    if values_by_gap:
        if set(values_by_gap) != {gap.gap_id for gap in item.gaps}:
            return None
        payload["gaps"] = [
            {**gap_payload, "accepted_values": list(values_by_gap[gap_payload["gap_id"]])}
            for gap_payload in payload["gaps"]
        ]
    payload["answer_key"] = NativeAnswerKey(
        origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED,
        correct_choice_ids=suggestion.correct_choice_ids,
        match_pairs=suggestion.match_pairs,
    ).model_dump()
    try:
        return NativeExamItem.model_validate(payload)
    except ValidationError:
        return None


def apply_suggestion_to_item(
    item: NativeExamItem,
    suggestion: NativeAnswerKeySuggestion,
) -> NativeExamItem:
    """Write an arriving suggestion onto its question (T5, P12, P13).

    The suggestion is always kept on the item. It also becomes the key, as
    ``machine_proposed`` with review required, only where the item's key
    follows arrivals and the suggestion fits the question.
    """

    if _follows_arrivals(item):
        keyed = _item_with_suggestion_key(item, suggestion)
        if keyed is not None:
            return keyed
    return item.model_copy(update={"ai_suggestion": suggestion})


def restore_suggestion_on_item(item: NativeExamItem) -> NativeExamItem:
    """Make the kept suggestion the key again: machine_proposed, review required (T6).

    A kept suggestion that no longer fits the question is refused (P13).
    """

    if item.ai_suggestion is None:
        return item
    keyed = _item_with_suggestion_key(item, item.ai_suggestion)
    if keyed is None:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Facitförslaget passar inte längre frågan.",
            details={"item_id": item.item_id},
        )
    return keyed
