"""Questions as a student meets them, read from a gold exam or a native document.

A question is a standalone item or one child of a parent. Both sides are flattened to the
same ordered questions; a parent's instruction belongs to each of its children.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
    NativeItemReviewState,
    NativeParseOrigin,
)

from .compare_text import CELL_SEPARATOR, ENTRY_LABEL, words
from .gold import GoldItem, GoldKind, GoldParent


@dataclass(frozen=True)
class Question:
    """What a student meets and how they are scored."""

    source_label: str
    kind: GoldKind
    points: int | float | None
    title: str
    instruction: tuple[str, ...]
    body: tuple[str, ...]
    # Whether a model converted the item; a review item built from source is not converted.
    converted: bool
    choices: tuple[str, ...] = ()
    correct_choices: tuple[str, ...] = ()
    gaps: tuple[tuple[str, ...], ...] = ()
    match_left: tuple[str, ...] = ()
    match_right: tuple[str, ...] = ()
    pairs: tuple[tuple[str, str], ...] = ()

    def entries(self) -> tuple[str, ...]:
        return (*self.choices, *self.match_left, *self.match_right)


@dataclass(frozen=True)
class GoldQuestion:
    item: GoldItem
    view: Question


def _is_table_row(line: str, lefts: set[str]) -> bool:
    return (
        CELL_SEPARATOR in line
        or ENTRY_LABEL.match(line) is not None
        or words(ENTRY_LABEL.sub("", line)) in lefts
    )


def _read_table(item: GoldItem) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """A matching prompt as its instruction lines and its two lists in source order.

    The table starts at the first row; a row of two cells holds a left and a right entry, and
    a single cell is a left entry when it is a gold pair's left text, otherwise a distractor.
    """
    lines = item.prompt.split("\n")
    lefts = {words(pair.left) for pair in item.pairs}
    start = next((i for i, line in enumerate(lines) if _is_table_row(line, lefts)), len(lines))
    left: list[str] = []
    right: list[str] = []
    for row in lines[start:]:
        cells = [ENTRY_LABEL.sub("", cell) for cell in row.split(CELL_SEPARATOR)]
        if len(cells) >= 2:
            left.append(cells[0])
            right.append(cells[1])
        elif words(cells[0]) in lefts:
            left.append(cells[0])
        else:
            right.append(cells[0])
    return tuple(lines[:start]), tuple(left), tuple(right)


def _gold_view(item: GoldItem, label: str, instruction: tuple[str, ...]) -> Question:
    body: tuple[str, ...] = tuple(item.prompt.split("\n"))
    left: tuple[str, ...] = ()
    right: tuple[str, ...] = ()
    if item.kind == "matching":
        body, left, right = _read_table(item)
    return Question(
        source_label=label,
        kind=item.kind,
        points=item.points,
        title="",
        instruction=instruction,
        body=body,
        converted=True,
        choices=item.choices,
        correct_choices=item.correct_choices,
        gaps=tuple(gap.accepted_values for gap in item.gaps),
        match_left=left,
        match_right=right,
        pairs=tuple((pair.left, pair.right) for pair in item.pairs),
    )


def gold_questions(items: Sequence[GoldItem | GoldParent]) -> tuple[GoldQuestion, ...]:
    """The gold exam's questions in order; a parent's children carry its instruction."""
    questions: list[GoldQuestion] = []
    for entry in items:
        if isinstance(entry, GoldParent):
            instruction = tuple(entry.instruction.split("\n"))
            for child in entry.children:
                label = f"{entry.source_label} / {child.source_label}"
                questions.append(GoldQuestion(child, _gold_view(child, label, instruction)))
        else:
            questions.append(GoldQuestion(entry, _gold_view(entry, entry.source_label, ())))
    return tuple(questions)


def _native_view(item: NativeExamItem, label: str, instruction: tuple[str, ...]) -> Question:
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
    return Question(
        source_label=label,
        kind=kind,
        points=item.points,
        title=item.title or "",
        instruction=instruction,
        body=item.plain_text_lines(),
        converted=item.review.parse_origin is NativeParseOrigin.LLM_PARSED,
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


def native_questions(document: NativeExamDocument) -> tuple[Question, ...]:
    """The document's items in order, each carrying the instruction of the parent that holds it."""
    parent_of = {item_id: parent for parent in document.parents for item_id in parent.item_ids}
    questions: list[Question] = []
    for item in document.items:
        parent = parent_of.get(item.item_id)
        if parent is None:
            questions.append(_native_view(item, item.item_id, ()))
        else:
            label = f"{parent.parent_id} / {item.item_id}"
            questions.append(_native_view(item, label, tuple(parent.instruction)))
    return tuple(questions)
