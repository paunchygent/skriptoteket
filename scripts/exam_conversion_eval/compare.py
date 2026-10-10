"""Compare exam substance without importing or running a converter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
    NativeItemReviewState,
)

from .gold import GoldExam, GoldGap, GoldItem, GoldKind, GoldPair


@dataclass(frozen=True)
class FieldMismatch:
    field: str
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


@dataclass(frozen=True)
class _ObservedItem:
    source_label: str
    kind: GoldKind
    points: int | float | None
    prompt: str
    choices: tuple[str, ...]
    correct_choices: tuple[str, ...]
    gaps: tuple[GoldGap, ...]
    pairs: tuple[GoldPair, ...] = ()


def _text(value: str) -> str:
    return " ".join(value.split())


def _texts(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({_text(value) for value in values}))


def compare_items(expected: GoldItem, actual: GoldItem) -> tuple[FieldMismatch, ...]:
    return _compare_item(expected, actual)


def _compare_item(
    expected: GoldItem, actual: GoldItem | _ObservedItem
) -> tuple[FieldMismatch, ...]:
    mismatches: list[FieldMismatch] = []

    def check(field: str, gold: object, observed: object) -> None:
        if gold != observed:
            mismatches.append(FieldMismatch(field, "different", gold, observed))

    if expected.teacher_questions:
        mismatches.append(
            FieldMismatch("teacher_questions", "gold_unresolved", expected.teacher_questions, ())
        )
    check("kind", expected.kind, actual.kind)
    check("points", expected.points, actual.points)
    check("prompt", _text(expected.prompt), _text(actual.prompt))
    check("choices", _texts(expected.choices), _texts(actual.choices))
    check("correct_choices", _texts(expected.correct_choices), _texts(actual.correct_choices))
    check("gaps", len(expected.gaps), len(actual.gaps))
    all_gold_answers = tuple(value for gap in expected.gaps for value in gap.accepted_values)
    for index, (gold_gap, observed_gap) in enumerate(zip(expected.gaps, actual.gaps, strict=False)):
        gold_answers = {normalize_answer(value) for value in gold_gap.accepted_values}
        observed_answers = {normalize_answer(value) for value in observed_gap.accepted_values}
        field = f"gaps[{index}].accepted_values"
        missing = gold_answers - observed_answers
        if missing:
            mismatches.append(FieldMismatch(field, "missing_answers", tuple(sorted(missing)), ()))
        extras = {
            answer
            for answer in observed_answers - gold_answers
            if not any(
                is_allowed_answer_spelling_variant(
                    gold, answer, other_gold_answers=all_gold_answers
                )
                for gold in gold_answers
            )
        }
        if extras:
            mismatches.append(FieldMismatch(field, "extra_answers", (), tuple(sorted(extras))))
    check(
        "pairs",
        tuple(sorted({(_text(pair.left), _text(pair.right)) for pair in expected.pairs})),
        tuple(sorted({(_text(pair.left), _text(pair.right)) for pair in actual.pairs})),
    )
    return tuple(mismatches)


def compare_exam(expected: GoldExam, actual: Sequence[GoldItem]) -> ExamComparison:
    return _compare_exam(expected, actual)


def _compare_exam(expected: GoldExam, actual: Sequence[GoldItem | _ObservedItem]) -> ExamComparison:
    results: list[ItemComparison] = []
    for index in range(max(len(expected.items), len(actual))):
        if index >= len(expected.items):
            observed = actual[index]
            results.append(
                ItemComparison(
                    index,
                    observed.source_label,
                    (FieldMismatch("item", "extra_item", None, observed),),
                )
            )
        elif index >= len(actual):
            gold = expected.items[index]
            mismatches = list(_compare_item(gold, gold))
            mismatches.append(FieldMismatch("item", "missing_item", gold, None))
            results.append(ItemComparison(index, gold.source_label, tuple(mismatches)))
        else:
            gold = expected.items[index]
            results.append(
                ItemComparison(index, gold.source_label, _compare_item(gold, actual[index]))
            )
    return ExamComparison(expected.confirmed, expected.confirmation_note, tuple(results))


def _project_native(item: NativeExamItem) -> _ObservedItem:
    kind: GoldKind = item.kind.value
    if (
        item.kind is NativeExamItemKind.FREE_TEXT
        and item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    ):
        kind = "review"
    gap_by_id = {gap.gap_id: gap for gap in item.gaps}
    ordered_gaps = tuple(
        GoldGap(accepted_values=gap_by_id[segment.gap_id].accepted_values)
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeGapSegment)
    )
    correct_ids = set(item.answer_key.correct_choice_ids)
    return _ObservedItem(
        source_label=item.item_id,
        kind=kind,
        points=item.points,
        prompt="\n".join(item.plain_text_lines()),
        choices=tuple(choice.text for choice in item.choices),
        correct_choices=tuple(
            choice.text for choice in item.choices if choice.choice_id in correct_ids
        ),
        gaps=ordered_gaps,
    )


def compare_native_exam(expected: GoldExam, document: NativeExamDocument) -> ExamComparison:
    return _compare_exam(expected, tuple(_project_native(item) for item in document.items))
