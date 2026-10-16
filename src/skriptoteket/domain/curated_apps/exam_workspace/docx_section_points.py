"""Split of a printed section total over the section's items that print no points (D38)."""

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import (
    matching_score,
    point_shares,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    points_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
    NativeExamItemKind,
)

AcceptedItem = tuple[NativeExamItem, tuple[str, ...]]


@dataclass(frozen=True)
class SectionPoints:
    """Items after the split and the points lines the split absorbed.

    ``absorbed`` holds unbuilt chunks that only restate a section's total after its last
    question; they are section metadata, never review items.
    """

    accepted: tuple[AcceptedItem, ...]
    absorbed: frozenset[str]
    # Source questions whose allocated share cannot yield a positive tick value.
    # The application uses its ordinary source-review fallback for these anchors.
    review_anchors: tuple[tuple[str, ...], ...] = ()


def _number(label: str) -> int | None:
    number = re.search(r"\d+", label)
    return int(number.group()) if number else None


def _line_total(chunk: DocxChunk) -> int | None:
    labels = POINT_LABEL.findall(chunk.text)
    return _number(labels[0]) if points_line(chunk.text) and len(labels) == 1 else None


def _total(
    instruction: ProducedMetadata, chunks: tuple[DocxChunk, ...], positions: dict[str, int]
) -> int | None:
    """The instruction's total, or the one total its section heading prints."""
    if instruction.points is not None:
        return instruction.points
    headings = [chunks[positions[a]] for a in instruction.source_anchors]
    labels = [
        label
        for chunk in headings
        if chunk.kind == "heading"
        for label in POINT_LABEL.findall(chunk.text)
    ]
    return _number(labels[0]) if len(labels) == 1 else None


def _closes(
    instruction: ProducedMetadata,
    chunks: tuple[DocxChunk, ...],
    positions: dict[str, int],
    first_question: int,
) -> bool:
    """A points line after a question that is no heading prints the points of what precedes it."""
    return all(
        positions[a] > first_question
        and chunks[positions[a]].kind != "heading"
        and points_line(chunks[positions[a]].text)
        for a in instruction.source_anchors
    )


def split_section_totals(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[AcceptedItem, ...],
    instructions: tuple[ProducedMetadata, ...],
    unbuilt: frozenset[str],
    *,
    questions: tuple[tuple[str, ...], ...] = (),
) -> SectionPoints:
    """Give each item in a section that prints no points a share of what remains (D38).

    A section starts at an instruction that prints a total, at a section heading whose
    one printed total the model left out, or at an unbuilt heading that prints one total,
    and runs to the next such start or to the end of the document. An instruction that is
    only a points line, not a heading, after the first question closes the questions
    before it and starts no section. A member prints its own points only when a chunk from
    its start to the next member's start prints them; points the model gave a member whose
    source prints none are not the member's own. In a section of two or more members, a
    points line after the last question that restates the section's total is the
    section's points line, never a question's own points and never unbuilt: it is
    absorbed. With one member that line is the question's own points.

    Printed points stay. The total less the points of members that print them is split
    over the members that print none, in document order, in whole points as evenly as
    possible, earlier members taking the extra point. A member whose share is no point,
    because nothing remains, keeps the model's own reading. A member given a share has its
    points marked as estimated (D6).
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    # A grouped question's heading belongs to its question-wide score pass, not
    # to the section estimate. This applies whether the producer claimed it or not.
    question_by_anchor = {anchor: own for own in questions for anchor in own}
    question_headings = frozenset(
        chunk.anchor
        for chunk in chunks
        if chunk.kind == "heading" and chunk.anchor in question_by_anchor
    )
    instructions = tuple(
        instruction
        for instruction in instructions
        if not question_headings.intersection(instruction.source_anchors)
    )
    starts = [min(positions[anchor] for anchor in anchors) for _, anchors in accepted]
    first_question = min(starts, default=len(chunks))
    totals = [(instruction, _total(instruction, chunks, positions)) for instruction in instructions]
    starting = {
        min(instruction.source_anchors, key=positions.__getitem__): total
        for instruction, total in totals
        if total is not None and not _closes(instruction, chunks, positions, first_question)
    }
    for anchor in unbuilt - question_headings:
        if anchor in positions and anchor not in starting:
            heading = ProducedMetadata(text="heading", source_anchors=(anchor,))
            if (total := _total(heading, chunks, positions)) is not None:
                starting[anchor] = total
    sections = sorted((positions[first], total) for first, total in starting.items())
    updated = list(accepted)
    absorbed: set[str] = set()
    review_anchors: list[tuple[str, ...]] = []
    for index, (start, total) in enumerate(sections):
        end = sections[index + 1][0] if index + 1 < len(sections) else len(chunks)
        members = sorted(
            (i for i, position in enumerate(starts) if start <= position < end),
            key=starts.__getitem__,
        )
        if not members:
            continue
        owners = {question_by_anchor.get(accepted[i][0].source_anchor or "") for i in members}
        if len(owners) == 1 and None not in owners:
            # All of this section's outputs belong to one grouped question. Its
            # printed total is applied atomically after heading placement instead.
            continue
        last_start = starts[members[-1]]
        closing = (
            {chunk.anchor for chunk in chunks[last_start + 1 : end] if _line_total(chunk) == total}
            if len(members) > 1
            else set()
        )
        bounds = sorted({starts[i] for i in members} | {end})
        spans = {i: chunks[starts[i] : bounds[bounds.index(starts[i]) + 1]] for i in members}
        printing = {
            i
            for i in members
            # Criteria already determine this item's points (Q12/R14), even when
            # the prompt prints none. A section estimate must not overwrite their sum.
            if accepted[i][0].criteria
            or any(
                POINT_LABEL.search(chunk.text) for chunk in spans[i] if chunk.anchor not in closing
            )
        }
        unprinted = [i for i in members if i not in printing]
        if not unprinted:
            continue
        absorbed.update(closing & unbuilt)
        remaining = int(total - sum(accepted[i][0].points or 0 for i in printing))
        shares = point_shares(max(remaining, 0), len(unprinted))
        for i, guess in zip(unprinted, shares, strict=True):
            item, anchors = accepted[i]
            if guess > 0:
                if item.kind is NativeExamItemKind.MATCHING:
                    # An unkeyed grid has no ticks from which to derive a positive total.
                    if item.answer_key.match_pairs:
                        try:
                            tick_points, points, _ = matching_score(
                                guess, len(item.answer_key.match_pairs)
                            )
                        except ValueError:
                            review_anchors.append(anchors)
                            continue
                        item = item.model_copy(
                            update={
                                "tick_points": tick_points,
                                "points": points,
                                "points_estimated": True,
                            }
                        )
                else:
                    item = item.model_copy(update={"points": guess, "points_estimated": True})
            updated[i] = (item, anchors)
    return SectionPoints(tuple(updated), frozenset(absorbed), tuple(review_anchors))
