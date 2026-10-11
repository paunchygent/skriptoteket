"""Principles 2 and 4: the answer key and answers kept out of sight."""

from __future__ import annotations

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    defines,
    short_form_definitions,
    slash_alternatives,
)

from .compare_questions import GoldQuestion, Question
from .compare_results import FieldMismatch
from .compare_text import occurrences, stream, words

# A teacher note labels its facit: a word and a colon, then the answer.
_FACIT_LABEL = re.compile(r"\w+:")


def _word_set(values: Iterable[str]) -> frozenset[str]:
    return frozenset(phrase for value in values if (phrase := words(value)))


def _admitted_extra(
    answer: str, gold_answers: set[str], definitions: list[tuple[str, str]]
) -> bool:
    """An extra answer within the spelling policy or among the forms rule 3 admits."""
    if any(is_allowed_answer_spelling_variant(gold, answer) for gold in gold_answers):
        return True
    forms = gold_answers | {
        normalize_answer(part) for gold in gold_answers for part in slash_alternatives(gold)
    }
    if answer in forms:
        return True
    for short, rest in definitions:
        short_form = normalize_answer(short)
        if answer == short_form and any(defines(rest, form) for form in forms):
            return True
        if short_form in forms and defines(rest, answer):
            return True
    return False


def scoring(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 2: same correct choices, every gold answer accepted, same pairs."""
    expected = gold.item
    mismatches: list[FieldMismatch] = []
    if _word_set(expected.correct_choices) != _word_set(actual.correct_choices):
        mismatches.append(
            FieldMismatch(
                "scoring",
                "correct_choices",
                tuple(expected.correct_choices),
                tuple(actual.correct_choices),
            )
        )
    # The instructions that define a short form are the parent's or the item's own.
    definitions = short_form_definitions([*gold.view.instruction, expected.prompt])
    gold_by_gap = [{normalize_answer(v) for v in gap.accepted_values} for gap in expected.gaps]
    for index, gold_answers in enumerate(gold_by_gap):
        observed = actual.gaps[index] if index < len(actual.gaps) else ()
        observed_answers = {normalize_answer(value) for value in observed}
        missing = gold_answers - observed_answers
        if missing:
            mismatches.append(
                FieldMismatch("scoring", f"gap {index + 1} misses", tuple(sorted(missing)), ())
            )
        other_gold = set().union(*(g for i, g in enumerate(gold_by_gap) if i != index))
        extras = {
            answer
            for answer in observed_answers - gold_answers
            if answer in other_gold or not _admitted_extra(answer, gold_answers, definitions)
        }
        if extras:
            mismatches.append(
                FieldMismatch(
                    "scoring", f"gap {index + 1} accepts extra", (), tuple(sorted(extras))
                )
            )
    gold_pairs = {(words(left), words(right)) for left, right in gold.view.pairs}
    observed_pairs = {(words(left), words(right)) for left, right in actual.pairs}
    if gold_pairs != observed_pairs:
        mismatches.append(
            FieldMismatch(
                "scoring", "pairs", tuple(sorted(gold_pairs)), tuple(sorted(observed_pairs))
            )
        )
    return mismatches


def facit_phrases(gold: GoldQuestion) -> set[str]:
    """What the teacher's facit says for an open question: the text after each note's last label."""
    if gold.item.kind not in ("free_text", "review"):
        return set()
    phrases: set[str] = set()
    for note in gold.item.notes:
        for line in note.split("\n"):
            labels = list(_FACIT_LABEL.finditer(line))
            if labels and (phrase := words(line[labels[-1].end() :])):
                phrases.add(phrase)
    return phrases


def leakage(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 4: no facit answer is shown more often than the gold question shows it.

    A parent's instruction is printed above each of its children, so it counts on both sides.
    """
    item = gold.item
    answers = {
        *(value for gap in item.gaps for value in gap.accepted_values),
        *item.correct_choices,
        *(pair.right for pair in item.pairs),
    }
    phrases = ({words(value) for value in answers} - {""}) | facit_phrases(gold)
    shown = stream([*actual.instruction, actual.title, *actual.body], gaps=True)
    expected = stream([*gold.view.instruction, *item.prompt.split("\n")], gaps=True)
    leaked = sorted(
        phrase for phrase in phrases if occurrences(shown, phrase) > occurrences(expected, phrase)
    )
    if leaked:
        return [FieldMismatch("no_answer_leakage", "facit_visible", (), tuple(leaked))]
    return []
