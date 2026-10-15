"""What Exam.net loses when it imports the QTI package of a native exam (Q15-Q17).

Purpose:
    List the teacher-facing repairs an Exam.net import needs: each Fritext question
    whose criterion text never enters the package, each shared-instruction
    subquestion Exam.net gives 1 point instead of its own, and each Lucktext whose
    points divide into rounded per-gap values below the question's total.

Relationships:
    - Built from the export's own items through
      `domain.curated_apps.exam_workspace.examnet_qti_export` and the scoring
      predicates of `domain.curated_apps.exam_conversion.examnet_qti_xml`, so the
      list cannot drift from the package.
    - Consumed by the exam workspace export handler behind the checklist route; the
      DigiExam converter lane has no checklist.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    emits_all_or_nothing,
    gap_point_values,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    NO_EXPORT_ASSETS,
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)

# The workspace row excerpt the panel shows (examWorkspaceRows.ts): the checklist
# question must read exactly as the row the teacher edits. The panel builds the
# row label from the bare sequence ("Fråga 3").
_QUESTION_TEXT_MAX_LENGTH = 140

# Exam.net gives a shared-instruction subquestion 1 point; a 1-point subquestion
# loses nothing (Q16).
_ALL_OR_NOTHING_MIN_POINTS = 2


@dataclass(frozen=True)
class ExamNetExportChecklistCriterion:
    """One Fritext criterion whose text Exam.net replaces with a bare row label."""

    text: str
    points: int


@dataclass(frozen=True)
class ExamNetExportChecklistFreeTextCriteria:
    """One Fritext question whose criteria import as unlabelled 1-point rows."""

    question_number: str
    question_text: str
    points: int | float
    criteria: tuple[ExamNetExportChecklistCriterion, ...]


@dataclass(frozen=True)
class ExamNetExportChecklistAllOrNothing:
    """One shared-instruction subquestion Exam.net gives 1 point instead of its own."""

    question_number: str
    question_text: str
    points: int | float


@dataclass(frozen=True)
class ExamNetExportChecklistRoundedGaps:
    """One Lucktext whose rounded per-gap value leaves part of its points unused."""

    question_number: str
    question_text: str
    points: int | float
    gap_points: int | float


ExamNetExportChecklistEntry: TypeAlias = (
    ExamNetExportChecklistFreeTextCriteria
    | ExamNetExportChecklistAllOrNothing
    | ExamNetExportChecklistRoundedGaps
)


def native_exam_export_checklist(
    document: NativeExamDocument,
    *,
    assets_by_id: Mapping[str, bytes] = NO_EXPORT_ASSETS,
) -> tuple[ExamNetExportChecklistEntry, ...]:
    """List every loss the document's QTI package suffers on Exam.net import.

    The question list is read from the same QTI items the export builds, and each
    loss from the predicate the XML writer scores that item with. Entries stand in
    document order; an export where nothing is lost returns an empty tuple.
    """

    qti_items = native_exam_to_examnet_qti_items(document, assets_by_id=assets_by_id)
    native_by_sequence = {item.sequence: item for item in document.items}
    entries: list[ExamNetExportChecklistEntry] = []
    for qti_item in qti_items:
        leaves = qti_item.children or (qti_item,)
        for leaf in leaves:
            native_item = _native_item_by_sequence(native_by_sequence, leaf.sequence)
            entry = _loss_entry(
                qti_item=leaf,
                native_item=native_item,
                shared_subquestion=bool(qti_item.children),
            )
            if entry is not None:
                entries.append(entry)
    return tuple(entries)


def _native_item_by_sequence(
    native_by_sequence: Mapping[int, NativeExamItem], sequence: int
) -> NativeExamItem:
    """The native question behind one exported leaf, named by its own sequence."""

    native_item = native_by_sequence.get(sequence)
    if native_item is None:
        raise ValueError(f"QTI item sequence {sequence} has no native question")
    return native_item


def _loss_entry(
    *,
    qti_item: ExamNetQtiItem,
    native_item: NativeExamItem,
    shared_subquestion: bool,
) -> ExamNetExportChecklistEntry | None:
    """The one way this question loses on import; item kinds never overlap losses."""

    if qti_item.interaction_type is ExamNetQtiInteractionType.FREE_TEXT:
        return _free_text_criteria_entry(qti_item=qti_item, native_item=native_item)
    if qti_item.interaction_type is ExamNetQtiInteractionType.GAP_FILL:
        return _rounded_gaps_entry(qti_item=qti_item, native_item=native_item)
    if not shared_subquestion:
        # A standalone keyed item imports one all-or-nothing rule worth its own
        # points (Q16); only a shared subquestion drops to Exam.net's 1 point.
        return None
    return _all_or_nothing_entry(qti_item=qti_item, native_item=native_item)


def _free_text_criteria_entry(
    *, qti_item: ExamNetQtiItem, native_item: NativeExamItem
) -> ExamNetExportChecklistFreeTextCriteria | None:
    """The Fritext criteria loss, selected by the export's own scoring decision (Q13).

    A Fritext without criteria is one row worth its points and loses nothing; an
    unkeyed Fritext carries no rule rows at all to label.
    """

    if qti_item.free_text_criterion_points is None or not native_item.criteria:
        return None
    if qti_item.max_score is None:
        return None
    return ExamNetExportChecklistFreeTextCriteria(
        question_number=_question_number(native_item),
        question_text=_question_text(native_item),
        points=qti_item.max_score,
        criteria=tuple(
            ExamNetExportChecklistCriterion(text=criterion.text, points=criterion.points)
            for criterion in native_item.criteria
        ),
    )


def _all_or_nothing_entry(
    *, qti_item: ExamNetQtiItem, native_item: NativeExamItem
) -> ExamNetExportChecklistAllOrNothing | None:
    """The shared-subquestion loss the XML writer scores all-or-nothing (Q16)."""

    if not emits_all_or_nothing(qti_item):
        return None
    points = qti_item.max_score
    if points is None or points < _ALL_OR_NOTHING_MIN_POINTS:
        return None
    return ExamNetExportChecklistAllOrNothing(
        question_number=_question_number(native_item),
        question_text=_question_text(native_item),
        points=points,
    )


def _rounded_gaps_entry(
    *, qti_item: ExamNetQtiItem, native_item: NativeExamItem
) -> ExamNetExportChecklistRoundedGaps | None:
    """The Lucktext loss the writer's own gap value split causes (Q17)."""

    gap_points = _rounded_gap_points(qti_item)
    if gap_points is None:
        return None
    points = qti_item.max_score
    if points is None:
        return None
    return ExamNetExportChecklistRoundedGaps(
        question_number=_question_number(native_item),
        question_text=_question_text(native_item),
        points=points,
        gap_points=gap_points,
    )


def _rounded_gap_points(qti_item: ExamNetQtiItem) -> int | float | None:
    """The value every gap gets, or None when the points divide evenly (Q17).

    Returns the writer's own rounded value; 0 names the edge where the floored
    share is 0.00, for which the writer writes no gap mapping at all. Whether
    Exam.net then imports such a gap as 0 points is unproven; the entry reports
    the rounded value the export itself carries, not an observed import result.
    """

    if qti_item.interaction_type is not ExamNetQtiInteractionType.GAP_FILL:
        return None
    if not qti_item.text_entry_gaps or qti_item.max_score is None:
        return None
    rounded = gap_point_values(qti_item)
    if rounded is None:
        return 0
    per_gap = Decimal(rounded[0])
    if per_gap * len(qti_item.text_entry_gaps) == Decimal(str(qti_item.max_score)):
        return None
    return _points_number(per_gap)


def _question_number(item: NativeExamItem) -> str:
    """The question's sequence as a string; the panel prints it as the row label."""

    return str(item.sequence)


def _question_text(item: NativeExamItem) -> str:
    """The start of the question's own text, as the workspace excerpt shows it."""

    flattened = " ".join(item.plain_text_lines())
    text = " ".join(flattened.split())
    if len(text) <= _QUESTION_TEXT_MAX_LENGTH:
        return text
    return f"{text[: _QUESTION_TEXT_MAX_LENGTH - 1].rstrip()}…"


def _points_number(value: Decimal) -> int | float:
    """A rounded 2-decimal value as the JSON number it prints (1.33, but 2 not 2.00)."""

    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)
