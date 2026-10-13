"""Principle 5: no gold wording is lost.

Every word of a gold question's prompt and instruction, its parent's instruction included, is
present somewhere in the converted question: its body, choices, match entries or the
parent's instruction. Which field holds a word, the word order and the line breaks do not count.
"""

from __future__ import annotations

from .compare_questions import GoldQuestion, Question
from .compare_results import FieldMismatch
from .compare_text import without_list_labels, word_set


def content(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 5: every word of the gold wording appears."""
    view = gold.view
    wanted = word_set(
        without_list_labels([*view.instruction, *view.body, *view.match_left, *view.match_right])
    )
    shown = word_set([*actual.instruction, *actual.body, *actual.entries()])
    missing = wanted - shown
    if missing:
        return [FieldMismatch("content_present", "missing_wording", tuple(sorted(missing)), ())]
    return []
