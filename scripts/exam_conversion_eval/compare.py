"""Judge a conversion against gold by the eight conversion principles, not textual identity.

TASK-SKRIPT-39-05-03 states the principles. The gold file is one correct conversion: a
converted item passes when a student meets the same question, answers it the same way
and is scored the same, and the item adds nothing Exam.net owns or that reveals an answer.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    defines,
    short_form_definitions,
    slash_alternatives,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
    NativeItemReviewState,
)

from .gold import GoldExam, GoldItem, GoldKind

Principle = Literal[
    "segmentation",
    "response_kind",
    "response_slots",
    "scoring",
    "points",
    "no_answer_leakage",
    "no_platform_labels",
    "content_present",
    "gold",
]
PRINCIPLES: tuple[Principle, ...] = (
    "segmentation",
    "response_kind",
    "response_slots",
    "scoring",
    "points",
    "no_answer_leakage",
    "no_platform_labels",
    "content_present",
)

_GAP_MARKER = "[___]"
_WORD = re.compile(r"\w+")
# A label Exam.net prints itself: an option letter or number before a choice or match entry.
_OPTION_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,2})\s*[.):]\s+\S")
# A source label opening the question: its number, alone or after a question word.
_QUESTION_NUMBER = re.compile(
    r"^\s*(?:(?:fråga|question|uppgift|task)\s*\d+|\d{1,3}\s*[.)](?!\d))", re.IGNORECASE
)
_POINT_LABEL = re.compile(
    r"\(\s*\d+(?:[.,]\d+)?\s*(?:p|poäng|points?|pts?)\.?\s*\)"
    r"|\b\d+(?:[.,]\d+)?\s*(?:poäng|points?)\b",
    re.IGNORECASE,
)
_BLANK_MARKER = re.compile(r"_{3,}|\.{4,}|…{2,}|\[\s*\]|\(\s*\)")
# A table row in a gold prompt separates its cells with " | "; a list entry opens with a label.
_CELL_SEPARATOR = " | "
_ENTRY_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,3})\s*[.)]\s+")
# A foreign stretch of another item must be long enough to identify that item.
_FOREIGN_MIN_WORDS = 5


@dataclass(frozen=True)
class FieldMismatch:
    principle: Principle
    reason: str
    expected: object
    actual: object


@dataclass(frozen=True)
class ItemComparison:
    index: int
    source_label: str
    mismatches: tuple[FieldMismatch, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def failed_principles(self) -> frozenset[Principle]:
        return frozenset(mismatch.principle for mismatch in self.mismatches)


@dataclass(frozen=True)
class ExamComparison:
    confirmed: bool
    confirmation_note: str | None
    items: tuple[ItemComparison, ...]

    @property
    def unconfirmed(self) -> bool:
        return not self.confirmed

    @property
    def passed(self) -> bool:
        """Substantive result; confirmation status remains separate metadata."""
        return all(item.passed for item in self.items)

    def failures_by_principle(self) -> dict[Principle, int]:
        """How many items fail each principle."""
        counts = Counter(p for item in self.items for p in item.failed_principles())
        return {principle: counts[principle] for principle in PRINCIPLES}


@dataclass(frozen=True)
class _ObservedItem:
    """What a student meets and how they are scored, from a native or gold item."""

    source_label: str
    kind: GoldKind
    points: int | float | None
    title: str | None
    body: tuple[str, ...]
    choices: tuple[str, ...] = ()
    correct_choices: tuple[str, ...] = ()
    gaps: tuple[tuple[str, ...], ...] = ()
    match_left: tuple[str, ...] = ()
    match_right: tuple[str, ...] = ()
    pairs: tuple[tuple[str, str], ...] = ()

    def own_text(self) -> tuple[str, ...]:
        return (self.title or "", *self.body)


def _words(text: str) -> str:
    """Wording alone: case, punctuation, quote style, line breaks and gap markers do not count."""
    return " ".join(_WORD.findall(text.replace(_GAP_MARKER, " ").casefold()))


def _joined_words(texts: Iterable[str]) -> str:
    return " ".join(words for text in texts if (words := _words(text)))


def _contains(haystack: str, needle: str) -> bool:
    return f" {needle} " in f" {haystack} "


def _occurrences(haystack: str, needle: str) -> int:
    return len(re.findall(rf"(?<!\S){re.escape(needle)}(?!\S)", haystack))


def _gold_pieces(prompt: str) -> tuple[str, ...]:
    """The gold prompt's wording per line and table cell, without list labels."""
    pieces = (
        _words(_ENTRY_LABEL.sub("", cell))
        for line in prompt.split("\n")
        for cell in line.split(_CELL_SEPARATOR)
    )
    return tuple(piece for piece in pieces if piece)


def _word_set(values: Iterable[str]) -> frozenset[str]:
    return frozenset(words for value in values if (words := _words(value)))


def _observed_gold(item: GoldItem) -> _ObservedItem:
    return _ObservedItem(
        source_label=item.source_label,
        kind=item.kind,
        points=item.points,
        title=None,
        body=tuple(item.prompt.split("\n")),
        choices=item.choices,
        correct_choices=item.correct_choices,
        gaps=tuple(gap.accepted_values for gap in item.gaps),
        match_left=tuple(dict.fromkeys(pair.left for pair in item.pairs)),
        match_right=tuple(dict.fromkeys(pair.right for pair in item.pairs)),
        pairs=tuple((pair.left, pair.right) for pair in item.pairs),
    )


def _observed_native(item: NativeExamItem) -> _ObservedItem:
    kind: GoldKind = item.kind.value
    if (
        item.kind is NativeExamItemKind.FREE_TEXT
        and item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    ):
        kind = "review"
    gap_by_id = {gap.gap_id: gap for gap in item.gaps}
    correct_ids = set(item.answer_key.correct_choice_ids)
    left = {entry.left_id: entry.text for entry in item.match_left}
    right = {entry.right_id: entry.text for entry in item.match_right}
    return _ObservedItem(
        source_label=item.item_id,
        kind=kind,
        points=item.points,
        title=item.title,
        body=item.plain_text_lines(),
        choices=tuple(choice.text for choice in item.choices),
        correct_choices=tuple(
            choice.text for choice in item.choices if choice.choice_id in correct_ids
        ),
        gaps=tuple(
            gap_by_id[segment.gap_id].accepted_values
            for paragraph in item.body
            for segment in paragraph.segments
            if isinstance(segment, NativeGapSegment)
        ),
        match_left=tuple(left.values()),
        match_right=tuple(right.values()),
        pairs=tuple(
            (left[pair.left_id], right[pair.right_id]) for pair in item.answer_key.match_pairs
        ),
    )


def _identifying_pieces(gold: Sequence[GoldItem]) -> tuple[frozenset[str], ...]:
    """Per gold item, its prompt stretches long enough to identify that item."""
    return tuple(
        frozenset(
            piece for piece in _gold_pieces(item.prompt) if len(piece.split()) >= _FOREIGN_MIN_WORDS
        )
        for item in gold
    )


def _segmentation(
    index: int, expected: GoldItem, actual: _ObservedItem, pieces: tuple[frozenset[str], ...]
) -> list[FieldMismatch]:
    """Principle 1: no text of another question is attached to this item."""
    own = _joined_words(actual.own_text())
    gold_words = _words(expected.prompt)
    foreign = sorted(
        {
            piece
            for other, identifying in enumerate(pieces)
            if other != index
            for piece in identifying
            if not _contains(gold_words, piece) and _contains(own, piece)
        }
    )
    if foreign:
        return [FieldMismatch("segmentation", "foreign_text", (), tuple(foreign))]
    return []


def _response_slots(expected: GoldItem, actual: _ObservedItem) -> list[FieldMismatch]:
    """Principle 3: the same gaps in number, the same options, the same two match lists."""
    mismatches: list[FieldMismatch] = []
    if len(expected.gaps) != len(actual.gaps):
        mismatches.append(
            FieldMismatch("response_slots", "gap_count", len(expected.gaps), len(actual.gaps))
        )
    gold = _observed_gold(expected)
    for field, gold_values, observed_values in (
        ("choices", gold.choices, actual.choices),
        ("match_left", gold.match_left, actual.match_left),
        ("match_right", gold.match_right, actual.match_right),
    ):
        if _word_set(gold_values) != _word_set(observed_values):
            mismatches.append(
                FieldMismatch(
                    "response_slots",
                    field,
                    tuple(sorted(_word_set(gold_values))),
                    tuple(sorted(_word_set(observed_values))),
                )
            )
    return mismatches


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


def _scoring(expected: GoldItem, actual: _ObservedItem) -> list[FieldMismatch]:
    """Principle 4: same correct choices, every gold answer accepted, same pairs."""
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
    definitions = short_form_definitions([expected.prompt])
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
    gold_pairs = {(_words(left), _words(right)) for left, right in _observed_gold(expected).pairs}
    observed_pairs = {(_words(left), _words(right)) for left, right in actual.pairs}
    if gold_pairs != observed_pairs:
        mismatches.append(
            FieldMismatch(
                "scoring", "pairs", tuple(sorted(gold_pairs)), tuple(sorted(observed_pairs))
            )
        )
    return mismatches


def _leakage(expected: GoldItem, actual: _ObservedItem) -> list[FieldMismatch]:
    """Principle 6: no facit answer is shown more often than the gold item shows it."""
    answers = {
        *(value for gap in expected.gaps for value in gap.accepted_values),
        *expected.correct_choices,
        *(pair.right for pair in expected.pairs),
    }
    own = _joined_words(actual.own_text())
    gold = _words(expected.prompt)
    leaked = sorted(
        answer
        for answer in {_words(value) for value in answers} - {""}
        if _occurrences(own, answer) > _occurrences(gold, answer)
    )
    if leaked:
        return [FieldMismatch("no_answer_leakage", "facit_visible", (), tuple(leaked))]
    return []


def _labels(expected: GoldItem, actual: _ObservedItem) -> list[FieldMismatch]:
    """Principle 7: no option letters, question numbers, point labels or printed blanks."""
    found: list[str] = []
    gold_entries = {_words(v) for v in (*expected.choices, *_observed_gold(expected).match_left)}
    for entry in (*actual.choices, *actual.match_left, *actual.match_right):
        if _OPTION_LABEL.match(entry) and _words(entry) not in gold_entries:
            found.append(f"option label: {entry}")
    own = [line for line in actual.own_text() if line.strip()]
    gold_lines = expected.prompt.split("\n")
    if own and _QUESTION_NUMBER.match(own[0]) and not _QUESTION_NUMBER.match(gold_lines[0]):
        found.append(f"question number: {own[0]}")
    own_text = "\n".join(own).replace(_GAP_MARKER, " ")
    gold_text = expected.prompt.replace(_GAP_MARKER, " ")
    for name, pattern in (("point label", _POINT_LABEL), ("blank marker", _BLANK_MARKER)):
        if len(pattern.findall(own_text)) > len(pattern.findall(gold_text)):
            found.append(f"{name}: {pattern.findall(own_text)}")
    if found:
        return [FieldMismatch("no_platform_labels", "label_visible", (), tuple(found))]
    return []


def _content(expected: GoldItem, actual: _ObservedItem) -> list[FieldMismatch]:
    """Principle 8: all gold student-visible wording is in the item's title, prompt or lists.

    Document instructions never reach the Exam.net export, so they do not count as visible.
    """
    visible = _joined_words((*actual.own_text(), *actual.match_left, *actual.match_right))
    missing = tuple(
        piece for piece in _gold_pieces(expected.prompt) if not _contains(visible, piece)
    )
    if missing:
        return [FieldMismatch("content_present", "missing_wording", missing, ())]
    return []


def _compare_item(
    index: int, expected: GoldItem, actual: _ObservedItem, pieces: tuple[frozenset[str], ...]
) -> tuple[FieldMismatch, ...]:
    mismatches: list[FieldMismatch] = []
    if expected.teacher_questions:
        mismatches.append(FieldMismatch("gold", "gold_unresolved", expected.teacher_questions, ()))
    mismatches.extend(_segmentation(index, expected, actual, pieces))
    if expected.kind != actual.kind:
        mismatches.append(FieldMismatch("response_kind", "kind", expected.kind, actual.kind))
    mismatches.extend(_response_slots(expected, actual))
    mismatches.extend(_scoring(expected, actual))
    if expected.points != actual.points:
        mismatches.append(FieldMismatch("points", "points", expected.points, actual.points))
    mismatches.extend(_leakage(expected, actual))
    mismatches.extend(_labels(expected, actual))
    mismatches.extend(_content(expected, actual))
    return tuple(mismatches)


def _compare_exam(expected: GoldExam, actual: Sequence[_ObservedItem]) -> ExamComparison:
    pieces = _identifying_pieces(expected.items)
    results: list[ItemComparison] = []
    for index in range(max(len(expected.items), len(actual))):
        if index >= len(expected.items):
            observed = actual[index]
            results.append(
                ItemComparison(
                    index,
                    observed.source_label,
                    (FieldMismatch("segmentation", "extra_item", None, observed),),
                )
            )
        elif index >= len(actual):
            gold = expected.items[index]
            results.append(
                ItemComparison(
                    index,
                    gold.source_label,
                    (FieldMismatch("segmentation", "missing_item", gold.source_label, None),),
                )
            )
        else:
            gold = expected.items[index]
            results.append(
                ItemComparison(
                    index, gold.source_label, _compare_item(index, gold, actual[index], pieces)
                )
            )
    return ExamComparison(expected.confirmed, expected.confirmation_note, tuple(results))


def compare_exam(expected: GoldExam, actual: Sequence[GoldItem]) -> ExamComparison:
    """Judge gold-shaped items, such as gold itself or an exam that converted nothing."""
    return _compare_exam(expected, tuple(_observed_gold(item) for item in actual))


def compare_native_exam(expected: GoldExam, document: NativeExamDocument) -> ExamComparison:
    return _compare_exam(expected, tuple(_observed_native(item) for item in document.items))
