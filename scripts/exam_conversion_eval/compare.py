"""Judge a conversion against gold by the eight conversion principles, not textual identity.

TASK-SKRIPT-39-05-03 states the principles. The gold file is one correct conversion: a
converted exam passes when each question, a standalone item or a child of a parent, shows a
student the same wording in the same order and place, is answered the same way and scored the
same, the questions sit under the same parents, and nothing Exam.net owns or any answer shows.
"""

from __future__ import annotations

from collections.abc import Sequence

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import points_line
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)

from .compare_answers import labels, leakage, scoring
from .compare_questions import GoldQuestion, Question, gold_questions, native_questions
from .compare_results import (
    PRINCIPLES,
    ExamComparison,
    FieldMismatch,
    ItemComparison,
    Principle,
    TitleComparison,
)
from .compare_structure import (
    all_phrases,
    content,
    membership_groups,
    parent_membership,
    segmentation,
    slots,
)
from .compare_text import words
from .gold import GoldExam, GoldItem, GoldParent

__all__ = [
    "PRINCIPLES",
    "ExamComparison",
    "FieldMismatch",
    "ItemComparison",
    "Principle",
    "TitleComparison",
    "compare_exam",
    "compare_native_exam",
]


def compare_title(
    gold_title: str, title: str | None, chunk_texts: Sequence[str]
) -> TitleComparison:
    """D12: the gold title, the source heading, or the heading with its printed subtitle.

    The heading is the source chunk whose words equal the gold title, or whose words with the
    next chunk's words equal it; the subtitle is the chunk after the heading. A line that prints
    points, such as an exam total, is no subtitle.
    """
    target = words(gold_title)
    accepted = {target}
    texts = [text for text in chunk_texts if words(text)]
    chunks = [words(text) for text in texts]
    for index, heading in enumerate(chunks):
        subtitle = (
            chunks[index + 1]
            if index + 1 < len(chunks) and not points_line(texts[index + 1])
            else None
        )
        if heading == target or (subtitle and f"{heading} {subtitle}" == target):
            accepted.add(heading)
            if subtitle:
                accepted.add(f"{heading} {subtitle}")
            break
    return TitleComparison(gold_title, title, title is not None and words(title) in accepted)


def _compare_question(
    gold: GoldQuestion, actual: Question, phrases: Sequence[str], membership: list[FieldMismatch]
) -> tuple[FieldMismatch, ...]:
    item = gold.item
    mismatches: list[FieldMismatch] = []
    if item.teacher_questions:
        mismatches.append(FieldMismatch("gold", "gold_unresolved", item.teacher_questions, ()))
    mismatches.extend(membership)
    mismatches.extend(segmentation(gold, actual, phrases))
    if item.kind != actual.kind:
        mismatches.append(FieldMismatch("response_kind", "kind", item.kind, actual.kind))
    mismatches.extend(slots(gold, actual))
    mismatches.extend(scoring(gold, actual))
    if item.points != actual.points:
        mismatches.append(FieldMismatch("points", "points", item.points, actual.points))
    mismatches.extend(leakage(gold, actual))
    mismatches.extend(labels(gold, actual))
    mismatches.extend(content(gold, actual))
    return tuple(mismatches)


def _compare_exam(
    expected: GoldExam, actual: Sequence[Question], title: TitleComparison
) -> ExamComparison:
    golds = gold_questions(expected.items)
    phrases = all_phrases(golds)
    gold_groups = membership_groups([gold.view.parent for gold in golds])
    actual_groups = membership_groups([question.parent for question in actual])
    results: list[ItemComparison] = []
    for index in range(max(len(golds), len(actual))):
        if index >= len(golds):
            observed = actual[index]
            mismatch = FieldMismatch("segmentation", "extra_item", None, observed)
            results.append(ItemComparison(index, observed.source_label, (mismatch,)))
        elif index >= len(actual):
            label = golds[index].view.source_label
            mismatch = FieldMismatch("segmentation", "missing_item", label, None)
            results.append(ItemComparison(index, label, (mismatch,)))
        else:
            membership = parent_membership(gold_groups[index], actual_groups[index])
            results.append(
                ItemComparison(
                    index,
                    golds[index].view.source_label,
                    _compare_question(golds[index], actual[index], phrases, membership),
                )
            )
    return ExamComparison(expected.confirmed, expected.confirmation_note, tuple(results), title)


def compare_exam(expected: GoldExam, actual: Sequence[GoldItem | GoldParent]) -> ExamComparison:
    """Judge gold-shaped items, such as gold itself or an exam that converted nothing."""
    title = TitleComparison(expected.title, expected.title, True)
    return _compare_exam(
        expected, tuple(question.view for question in gold_questions(actual)), title
    )


def compare_native_exam(
    expected: GoldExam, document: NativeExamDocument, source_chunks: Sequence[str] = ()
) -> ExamComparison:
    """Judge a native document; the source chunk texts let the title be the source heading."""
    title = compare_title(expected.title, document.title, source_chunks)
    return _compare_exam(expected, native_questions(document), title)
