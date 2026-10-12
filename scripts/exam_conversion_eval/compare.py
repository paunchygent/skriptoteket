"""Judge a conversion against gold by five principles a teacher would accept, not identity.

ST-SKRIPT-39-05 term A7: the gold file is one correct conversion, not the only one. A converted
exam passes when its title passes and each question, a standalone item or a child of a parent,
has gold's type, answer key and points, shows no facit answer, and loses no gold wording.
"""

from __future__ import annotations

from collections.abc import Sequence

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import points_line
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)

from .compare_answers import leakage, scoring
from .compare_questions import GoldQuestion, Question, gold_questions, native_questions
from .compare_results import (
    PRINCIPLES,
    ExamComparison,
    FieldMismatch,
    ItemComparison,
    Principle,
    TitleComparison,
)
from .compare_structure import content
from .compare_text import word_set, words
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


def _compare_question(gold: GoldQuestion, actual: Question) -> tuple[FieldMismatch, ...]:
    item = gold.item
    mismatches: list[FieldMismatch] = []
    if item.teacher_questions:
        mismatches.append(FieldMismatch("gold", "gold_unresolved", item.teacher_questions, ()))
    if item.kind != actual.kind:
        mismatches.append(FieldMismatch("response_kind", "kind", item.kind, actual.kind))
    mismatches.extend(scoring(gold, actual))
    if item.points != actual.points:
        mismatches.append(FieldMismatch("points", "points", item.points, actual.points))
    mismatches.extend(leakage(gold, actual))
    mismatches.extend(content(gold, actual))
    return tuple(mismatches)


# A parent's instruction is shared by its children, so it never tells siblings apart.
def _question_words(question: Question) -> frozenset[str]:
    return word_set((question.title, *question.body, *question.entries()))


def _pair_by_wording(golds: Sequence[GoldQuestion], actual: Sequence[Question]) -> dict[int, int]:
    """D33: gold and converted questions pair by shared wording, the largest overlap first.

    The overlap is the share of the gold question's words found in the converted question; a
    pair needs a shared word and a tie goes to the nearer position. Taking the largest overlap
    first lets a gold question without a counterpart claim only what is left over, so one
    merged, split or dropped question never takes the partner of a later one.
    Returns converted positions by gold position.
    """
    converted = [_question_words(question) for question in actual]
    candidates: list[tuple[float, int, int, int]] = []
    for position, gold in enumerate(golds):
        gold_words = _question_words(gold.view)
        for index, words_found in enumerate(converted):
            if shared := len(gold_words & words_found):
                candidates.append(
                    (-shared / len(gold_words), abs(index - position), position, index)
                )
    pairs: dict[int, int] = {}
    taken: set[int] = set()
    for _, _, position, index in sorted(candidates):
        if position not in pairs and index not in taken:
            pairs[position] = index
            taken.add(index)
    return pairs


def _compare_exam(
    expected: GoldExam, actual: Sequence[Question], title: TitleComparison
) -> ExamComparison:
    """D33, D34: a gold question pairs with the converted question of the most shared wording.

    A gold question without a pair is missing; a converted question without a pair is extra.
    """
    golds = gold_questions(expected.items)
    pairs = _pair_by_wording(golds, actual)
    results: list[ItemComparison] = []
    for position, gold in enumerate(golds):
        if position in pairs:
            mismatches = _compare_question(gold, actual[pairs[position]])
        else:
            mismatches = (
                FieldMismatch("content_present", "missing_item", gold.view.source_label, None),
            )
        results.append(ItemComparison(position, gold.view.source_label, mismatches))
    for index in sorted(set(range(len(actual))) - set(pairs.values())):
        observed = actual[index]
        mismatch = FieldMismatch("response_kind", "extra_item", None, observed)
        results.append(ItemComparison(len(results), observed.source_label, (mismatch,)))
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
