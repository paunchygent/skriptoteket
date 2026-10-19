"""Printed points reach the built items in one pass, after placement (D2, D38, D6).

The pass reads only ``PrintedPoints``: each question that prints its points takes them
over the reply first, then each part gives what remains of its total to its questions
that print none, inner parts before the outer part around them, and each part's total
checks the parent that holds exactly its items.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import point_shares
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    PrintedPart,
    PrintedPoints,
    PrintedQuestion,
    heading_openers,
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
    # The reader's number for each item's heading, in item order, or None:
    # a heading part opener's total, or a question-owned heading line's points.
    read_heading_points: tuple[int | float | None, ...]


def apply_printed_points(
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...],
    printed: PrintedPoints,
    by_anchor: Mapping[str, DocxChunk],
) -> ScoredItems:
    """Give every question's one item its printed points or its share of its part, in that
    order.

    A question that prints its points keeps them. Inner parts score first. In each part, the
    total less the points of its other questions goes to the questions that print none: one
    such question takes the exact remainder. An outer part ("Del 1") shares its total only
    over its questions that print no points and lie in no inner part ("Uppgift 1.2 (3 p)"):
    a question with its own points or inner total keeps that value and is never first given
    a share. Among two or more, a question whose criteria fix its points keeps
    them (Q12/R14) and the rest share what remains in whole points, as evenly as possible,
    earlier questions taking the extra point; such shares are marked estimated. A share of
    no point, or an unkeyed grid, keeps the model's own reading. The part's total then
    checks the parent that holds exactly the part's items; a parent over only some of them
    keeps its own total. When an inner part holds the same items as the outer part around
    it, the outer part's line opens the parent, so the outer total checks it; a parent with
    one child is checked the same way. A question's item is the item that starts at one of
    its own chunks, or at a part line that heads only that question (a ``heading_openers``
    part), which no question holds.
    """
    scored = list(items)
    events: list[DocxBuildEvent] = []

    # A question's item may start at the part line that heads it, which no question holds.
    opened = {part.opener: part.questions[0] for part in heading_openers(printed.parts)}

    def member(number: int) -> NativeExamItem | None:
        """The question's one item: the first item that starts at one of its own chunks, else
        the first that starts at the part line that heads this question."""
        own = set(printed.questions[number].anchors)
        first = next((item for item in scored if item.source_anchor in own), None)
        if first is not None:
            return first
        return next(
            (i for i in scored if i.source_anchor and opened.get(i.source_anchor) == number), None
        )

    def score(
        item: NativeExamItem, question: PrintedQuestion, points: int | float, *, estimated: bool
    ) -> None:
        nonlocal scored
        result = with_question_points(
            item,
            points,
            source_chunks=tuple(by_anchor[a] for a in question.anchors if a in by_anchor),
            estimated=estimated,
            source_points=question.points if question.prints else None,
        )
        events.extend(result.events)
        scored = [result.item if i.item_id == item.item_id else i for i in scored]

    for number, question in enumerate(printed.questions):
        if question.points is not None and (item := member(number)) is not None:
            score(item, question, question.points, estimated=False)
    # Inner parts (no part label) score their questions before an outer part shares its total,
    # and an outer part's total checks a parent after an inner part over the same items.
    inner_first = sorted(printed.parts, key=lambda p: p.identity is not None)
    for part in inner_first:
        inner = _inner_questions(part, printed.parts)
        flagged = [(number, number in inner) for number in part.questions]
        questions = [
            (printed.questions[n], item, nested)
            for n, nested in flagged
            if (item := member(n)) is not None
        ]
        unprinted = [(q, item) for q, item, nested in questions if not q.prints and not nested]
        sharing = (
            unprinted
            if len(unprinted) == 1
            else [(q, item) for q, item in unprinted if not item.criteria]
        )
        if not sharing:
            continue
        shared = {item.item_id for _, item in sharing}
        remaining = part.total - sum(
            item.points or 0 for _, item, _ in questions if item.item_id not in shared
        )
        if len(sharing) > 1:
            remaining = int(remaining)
        for (question, item), share in zip(
            sharing, point_shares(max(remaining, 0), len(sharing)), strict=True
        ):
            unkeyed = item.kind is NativeExamItemKind.MATCHING and not item.answer_key.match_pairs
            if share > 0 and not unkeyed:
                score(item, question, share, estimated=len(sharing) > 1)
    for part in inner_first:
        held = {item.item_id for number in part.questions if (item := member(number)) is not None}
        parents = tuple(
            parent.model_copy(update={"printed_total": part.total})
            if held and set(parent.item_ids) == held
            else parent
            for parent in parents
        )
    # The reader's number for each item's heading (D12 read-label correction):
    # a heading part opener's total, or the question's printed points when a
    # points line the question owns is a heading. The number goes only to the
    # one item holding the read heading chunk: the member whose question owns
    # the opener, or the item starting at the opener (``opened``); every other
    # member gets None. Two differing numbers give None, so the gate compares
    # with the settled points as before.
    read: dict[str, set[int | float]] = {item.item_id: set() for item in scored}
    for part in inner_first:
        opener = by_anchor.get(part.opener)
        if opener is None or opener.kind != "heading":
            continue
        holder: NativeExamItem | None = None
        for number in part.questions:
            if part.opener in printed.questions[number].anchors:
                holder = member(number)
                break
        if holder is None:
            first = opened.get(part.opener)
            if first is not None:
                holder = member(first)
        if holder is not None:
            read[holder.item_id].add(part.total)
    for number, question in enumerate(printed.questions):
        if question.points is None or (item := member(number)) is None:
            continue
        owned = [anchor for anchor, owner in printed.owners.items() if owner == number]
        headed = any(
            by_anchor.get(anchor) is not None and by_anchor[anchor].kind == "heading"
            for anchor in owned
        )
        if headed:
            read[item.item_id].add(question.points)
    reads: list[int | float | None] = []
    for item in scored:
        values = read[item.item_id]
        reads.append(next(iter(values)) if len(values) == 1 else None)
    return ScoredItems(tuple(scored), tuple(parents), tuple(events), tuple(reads))


def _inner_questions(part: PrintedPart, parts: tuple[PrintedPart, ...]) -> frozenset[int]:
    """The questions of an outer part that an inner part inside it totals.

    An outer part names its part ("Del 1"); an inner part names none ("Uppgift 1.2 (3 p)")
    and holds only questions of the outer part. A part that names none has no inner parts.
    """
    if part.identity is None:
        return frozenset()
    held = frozenset(part.questions)
    return frozenset(
        number
        for other in parts
        if other.identity is None and held.issuperset(other.questions)
        for number in other.questions
    )
