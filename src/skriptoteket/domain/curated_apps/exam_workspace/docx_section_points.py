"""Split of a printed section total over the section's items that print no points (D38)."""

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    points_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItem

AcceptedItem = tuple[NativeExamItem, tuple[str, ...]]

CHECK_POINTS_REASON = (
    "Frågan anger inga egna poäng, så poängen är en uppskattning utifrån avsnittets "
    "totalpoäng – kontrollera frågans poäng."
)


@dataclass(frozen=True)
class SectionPoints:
    """Items after the split and the points lines the split absorbed.

    ``absorbed`` holds unbuilt chunks that only restate a section's total after its last
    question; they are section metadata, never review items.
    """

    accepted: tuple[AcceptedItem, ...]
    absorbed: frozenset[str]


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
    because nothing remains, keeps the model's own reading. Every member that prints no
    points carries the check-points reason.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    starts = [min(positions[anchor] for anchor in anchors) for _, anchors in accepted]
    first_question = min(starts, default=len(chunks))
    totals = [(instruction, _total(instruction, chunks, positions)) for instruction in instructions]
    starting = {
        min(instruction.source_anchors, key=positions.__getitem__): total
        for instruction, total in totals
        if total is not None and not _closes(instruction, chunks, positions, first_question)
    }
    for anchor in unbuilt:
        if anchor in positions and anchor not in starting:
            heading = ProducedMetadata(text="heading", source_anchors=(anchor,))
            if (total := _total(heading, chunks, positions)) is not None:
                starting[anchor] = total
    sections = sorted((positions[first], total) for first, total in starting.items())
    updated = list(accepted)
    absorbed: set[str] = set()
    for index, (start, total) in enumerate(sections):
        end = sections[index + 1][0] if index + 1 < len(sections) else len(chunks)
        members = sorted(
            (i for i, position in enumerate(starts) if start <= position < end),
            key=starts.__getitem__,
        )
        if not members:
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
            if any(
                POINT_LABEL.search(chunk.text) for chunk in spans[i] if chunk.anchor not in closing
            )
        }
        unprinted = [i for i in members if i not in printing]
        if not unprinted:
            continue
        absorbed.update(closing & unbuilt)
        remaining = int(total - sum(accepted[i][0].points or 0 for i in printing))
        share, extra = divmod(max(remaining, 0), len(unprinted))
        for rank, i in enumerate(unprinted):
            item, anchors = accepted[i]
            guess = share + 1 if rank < extra else share
            reasons = tuple(dict.fromkeys((*item.review.reasons, CHECK_POINTS_REASON)))
            review = item.review.model_copy(update={"reasons": reasons})
            points = guess if guess > 0 else item.points
            updated[i] = (item.model_copy(update={"points": points, "review": review}), anchors)
    return SectionPoints(tuple(updated), frozenset(absorbed))
