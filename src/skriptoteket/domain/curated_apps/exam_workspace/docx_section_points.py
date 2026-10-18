"""Printed points reach the built items in one pass, after placement (D2, D38, D6).

The pass reads only ``PrintedPoints``: each question that prints its points takes them
over the reply first, then each part gives what remains of its total to its questions
that print none, and each part's total checks the parent that holds its items.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import point_shares
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    PrintedPoints,
    PrintedQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    replace_question_items,
    with_question_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent


@dataclass(frozen=True)
class ScoredItems:
    items: tuple[NativeExamItem, ...]
    parents: tuple[NativeExamParent, ...]
    events: tuple[DocxBuildEvent, ...]


def apply_printed_points(
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...],
    printed: PrintedPoints,
    by_anchor: Mapping[str, DocxChunk],
) -> ScoredItems:
    """Give every question its printed points or its share of its part, in that order.

    A question that prints its points keeps them. In each part, the total less the points
    of its other questions goes to the questions that print none: one such question takes
    the exact remainder. Among two or more, a question whose criteria fix its points keeps
    them (Q12/R14) and the rest share what remains in whole points, as evenly as possible,
    earlier questions taking the extra point; such shares are marked estimated. A share of
    no point, or an unkeyed grid, keeps the model's own reading. The part's total then
    checks the largest parent that holds only its items.
    """
    scored = list(items)
    events: list[DocxBuildEvent] = []

    def members(question: PrintedQuestion) -> tuple[NativeExamItem, ...]:
        own = set(question.anchors)
        return tuple(item for item in scored if item.source_anchor in own)

    def score(question: PrintedQuestion, points: int | float, *, estimated: bool) -> None:
        nonlocal scored, parents
        result = with_question_points(
            members(question),
            points,
            source_chunks=tuple(by_anchor[a] for a in question.anchors if a in by_anchor),
            estimated=estimated,
        )
        events.extend(result.events)
        scored, parents = replace_question_items(scored, parents, members(question), result)

    for question in printed.questions:
        if question.points is not None and members(question):
            score(question, question.points, estimated=False)
    for part in printed.parts:
        questions = [
            question
            for question in (printed.questions[number] for number in part.questions)
            if members(question)
        ]
        unprinted = [q for q in questions if not q.prints]
        sharing = (
            unprinted
            if len(unprinted) == 1
            else [q for q in unprinted if not any(item.criteria for item in members(q))]
        )
        if not sharing:
            continue
        remaining = part.total - sum(
            item.points or 0 for q in questions if q not in sharing for item in members(q)
        )
        if len(sharing) > 1:
            remaining = int(remaining)
        for question, share in zip(
            sharing, point_shares(max(remaining, 0), len(sharing)), strict=True
        ):
            unkeyed = any(
                item.kind is NativeExamItemKind.MATCHING and not item.answer_key.match_pairs
                for item in members(question)
            )
            if share > 0 and not unkeyed:
                score(question, share, estimated=len(sharing) > 1)
    for part in printed.parts:
        held = {
            item.item_id for number in part.questions for item in members(printed.questions[number])
        }
        inside = [
            (len(parent.item_ids), index)
            for index, parent in enumerate(parents)
            if parent.item_ids and held.issuperset(parent.item_ids)
        ]
        if inside:
            chosen = max(inside)[1]
            parents = tuple(
                parent.model_copy(update={"printed_total": part.total}) if i == chosen else parent
                for i, parent in enumerate(parents)
            )
    return ScoredItems(tuple(scored), tuple(parents), tuple(events))
