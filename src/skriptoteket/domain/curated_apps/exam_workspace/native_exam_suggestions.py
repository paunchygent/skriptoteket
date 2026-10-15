"""Validation of historical answer-key suggestions, independent of current item content."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
)


def validate_answer_key_suggestion(suggestion: NativeAnswerKeySuggestion | None) -> None:
    """Check the kept suggestion's own shape, never its currency.

    A suggestion is historical data for the question its fingerprint
    describes: after an answer-relevant edit — including a change of
    the question's kind — it may propose a key for another kind, name
    choices, match entries or gaps the question no longer declares,
    and it stays stored so the fingerprint can report it out of date.
    Only the suggestion's own shape is invariant here: exactly one
    payload family carries the proposed key (choice ids, match pairs
    or gap accepted values) and no entry is named twice within it.
    Producer validation against the requested question and the current
    answer key's constraints live in their own checks, so a stored
    historical suggestion never becomes a valid active key by storage.
    """

    if suggestion is None:
        return
    families = (
        bool(suggestion.correct_choice_ids),
        bool(suggestion.match_pairs),
        bool(suggestion.gap_accepted_values),
    )
    if sum(families) != 1:
        raise ValueError("a kept suggestion proposes exactly one kind of key")
    if len(set(suggestion.correct_choice_ids)) != len(suggestion.correct_choice_ids):
        raise ValueError("suggested choice ids must be unique")
    paired_left = [pair.left_id for pair in suggestion.match_pairs]
    if len(set(paired_left)) != len(paired_left):
        raise ValueError("a suggestion pairs each left entry at most once")
    paired_right = [pair.right_id for pair in suggestion.match_pairs]
    if len(set(paired_right)) != len(paired_right):
        raise ValueError("a suggestion pairs each right entry at most once")
    suggested_gap_ids = [entry.gap_id for entry in suggestion.gap_accepted_values]
    if len(set(suggested_gap_ids)) != len(suggested_gap_ids):
        raise ValueError("a suggestion names each gap at most once")
