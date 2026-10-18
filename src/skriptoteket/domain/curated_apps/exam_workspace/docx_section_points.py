"""Printed points reach the built items in one pass, after placement (D2, D38, D6).

The pass reads only ``PrintedPoints``: each question that prints its points takes them
over the reply first, then each part gives what remains of its total to its questions
that print none, and each part's total checks the parent that holds exactly its items.
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
    """Give every question's one item its printed points or its share of its part, in that
    order.

    A question that prints its points keeps them. In each part, the total less the points
    of its other questions goes to the questions that print none: one such question takes
    the exact remainder. Among two or more, a question whose criteria fix its points keeps
    them (Q12/R14) and the rest share what remains in whole points, as evenly as possible,
    earlier questions taking the extra point; such shares are marked estimated. A share of
    no point, or an unkeyed grid, keeps the model's own reading. The part's total then
    checks the parent that holds exactly the part's items; a parent over only some of them
    keeps its own total.
    """
    scored = list(items)
    events: list[DocxBuildEvent] = []

    def member(question: PrintedQuestion) -> NativeExamItem | None:
        """The question's one item: the first item that starts at one of its own chunks."""
        own = set(question.anchors)
        return next((item for item in scored if item.source_anchor in own), None)

    def score(
        item: NativeExamItem, question: PrintedQuestion, points: int | float, *, estimated: bool
    ) -> None:
        nonlocal scored
        result = with_question_points(
            item,
            points,
            source_chunks=tuple(by_anchor[a] for a in question.anchors if a in by_anchor),
            estimated=estimated,
        )
        events.extend(result.events)
        scored = [result.item if i.item_id == item.item_id else i for i in scored]

    for question in printed.questions:
        if question.points is not None and (item := member(question)) is not None:
            score(item, question, question.points, estimated=False)
    for part in printed.parts:
        questions = [
            (question, item)
            for question in (printed.questions[number] for number in part.questions)
            if (item := member(question)) is not None
        ]
        unprinted = [(q, item) for q, item in questions if not q.prints]
        sharing = (
            unprinted
            if len(unprinted) == 1
            else [(q, item) for q, item in unprinted if not item.criteria]
        )
        if not sharing:
            continue
        shared = {item.item_id for _, item in sharing}
        remaining = part.total - sum(
            item.points or 0 for _, item in questions if item.item_id not in shared
        )
        if len(sharing) > 1:
            remaining = int(remaining)
        for (question, item), share in zip(
            sharing, point_shares(max(remaining, 0), len(sharing)), strict=True
        ):
            unkeyed = item.kind is NativeExamItemKind.MATCHING and not item.answer_key.match_pairs
            if share > 0 and not unkeyed:
                score(item, question, share, estimated=len(sharing) > 1)
    for part in printed.parts:
        held = {
            item.item_id
            for number in part.questions
            if (item := member(printed.questions[number])) is not None
        }
        parents = tuple(
            parent.model_copy(update={"printed_total": part.total})
            if held and set(parent.item_ids) == held
            else parent
            for parent in parents
        )
    return ScoredItems(tuple(scored), tuple(parents), tuple(events))
