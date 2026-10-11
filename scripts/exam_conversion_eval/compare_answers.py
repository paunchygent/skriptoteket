"""Principles 4, 6 and 7: scoring, answers kept out of sight, labels Exam.net owns."""

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
from .compare_text import GAP_MARKER, occurrences, stream, words

# A label Exam.net prints itself: an option letter or number before a choice or match entry.
_OPTION_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,2})\s*[.):]\s+\S")
# A source label opening a line: a question number, alone or after a question word.
_QUESTION_NUMBER = re.compile(
    r"^\s*(?:(?:fråga|question|uppgift|task)\s*\d+|\d{1,3}\s*[.)](?!\d))", re.IGNORECASE
)
_POINT_LABEL = re.compile(
    r"\(\s*\d+(?:[.,]\d+)?\s*(?:p|poäng|points?|pts?)\.?\s*\)"
    r"|\b\d+(?:[.,]\d+)?\s*(?:poäng|points?)\b",
    re.IGNORECASE,
)
_BLANK_MARKER = re.compile(r"_{3,}|\.{4,}|…{2,}|\[\s*\]|\(\s*\)")
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
    """Principle 4: same correct choices, every gold answer accepted, same pairs."""
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
    """Principle 6: no facit answer is shown more often than the gold question shows it."""
    item = gold.item
    answers = {
        *(value for gap in item.gaps for value in gap.accepted_values),
        *item.correct_choices,
        *(pair.right for pair in item.pairs),
    }
    phrases = ({words(value) for value in answers} - {""}) | facit_phrases(gold)
    shown = stream([actual.title, *actual.body], gaps=True)
    expected = stream(item.prompt.split("\n"), gaps=True)
    leaked = sorted(
        phrase for phrase in phrases if occurrences(shown, phrase) > occurrences(expected, phrase)
    )
    if leaked:
        return [FieldMismatch("no_answer_leakage", "facit_visible", (), tuple(leaked))]
    return []


def _numbered(lines: Iterable[str]) -> int:
    return sum(1 for line in lines if _QUESTION_NUMBER.match(line))


def labels(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 7: no option letters, question numbers, point labels or printed blanks."""
    view = gold.view
    found: list[str] = []
    gold_entries = {words(entry) for entry in view.entries()}
    for entry in actual.entries():
        if _OPTION_LABEL.match(entry) and words(entry) not in gold_entries:
            found.append(f"option label: {entry}")
    own_lines = [line for line in (actual.title, *actual.body) if line.strip()]
    if _numbered(own_lines) > _numbered(view.body):
        numbered = [line for line in own_lines if _QUESTION_NUMBER.match(line)]
        found.append(f"question number: {numbered}")
    own_text = "\n".join((*actual.instruction, *own_lines)).replace(GAP_MARKER, " ")
    gold_text = "\n".join((*view.instruction, *view.body)).replace(GAP_MARKER, " ")
    for name, pattern in (("point label", _POINT_LABEL), ("blank marker", _BLANK_MARKER)):
        if len(pattern.findall(own_text)) > len(pattern.findall(gold_text)):
            found.append(f"{name}: {pattern.findall(own_text)}")
    if found:
        return [FieldMismatch("no_platform_labels", "label_visible", (), tuple(found))]
    return []
