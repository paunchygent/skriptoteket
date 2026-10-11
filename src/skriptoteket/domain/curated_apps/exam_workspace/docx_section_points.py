"""Equal split of a printed section total over the section's items that print no points (D38)."""

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

CHECK_POINTS_REASON = "Poängen anges bara som totalpoäng för avsnittet – kontrollera frågans poäng."


@dataclass(frozen=True)
class SectionPoints:
    """Items after the split, sections left unsplit, and points lines the split absorbed.

    ``absorbed`` holds unbuilt chunks that only restate a section's total after its last
    question; they are section metadata, never review items.
    """

    accepted: tuple[AcceptedItem, ...]
    unsplit: tuple[str, ...]
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


def split_section_totals(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[AcceptedItem, ...],
    instructions: tuple[ProducedMetadata, ...],
    unbuilt: frozenset[str],
) -> SectionPoints:
    """Give each item in a section that prints no points an equal share of its total (D38).

    A section starts at an instruction that prints a total, at a section heading whose
    one printed total the model left out, or at an unbuilt heading that prints one total,
    and runs to the next such start or to the end of the document. A member prints its own
    points only when a chunk from its start to the next member's start prints them; points
    the model gave a member whose source prints none are not the member's own. A points
    line after the section's last question that restates the section's total is the
    section's points line, never a question's own points and never unbuilt: it is absorbed.

    The total is split only when the section has at least two members, every member prints
    no points, no other source chunk in the section went unbuilt, and the total divides
    evenly over the members. Every member that prints no points carries the check-points
    reason and, without a split, no points. A total over one question is that question's
    own printed points misread as a section total, so that section stays as it is.
    Sections whose members all print points, or that have no members, need no split;
    every other section left unsplit is reported by its first anchor.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    totals = [(instruction, _total(instruction, chunks, positions)) for instruction in instructions]
    starting = {
        min(instruction.source_anchors, key=positions.__getitem__): total
        for instruction, total in totals
        if total is not None
    }
    for anchor in unbuilt:
        if anchor in positions and anchor not in starting:
            heading = ProducedMetadata(text="heading", source_anchors=(anchor,))
            if (total := _total(heading, chunks, positions)) is not None:
                starting[anchor] = total
    sections = sorted((positions[first], first, total) for first, total in starting.items())
    starts = [min(positions[anchor] for anchor in anchors) for _, anchors in accepted]
    updated = list(accepted)
    unsplit: list[str] = []
    absorbed: set[str] = set()
    for index, (start, first_anchor, total) in enumerate(sections):
        end = sections[index + 1][0] if index + 1 < len(sections) else len(chunks)
        members = [i for i, position in enumerate(starts) if start <= position < end]
        if not members:
            continue
        last_start = max(starts[i] for i in members)
        closing = {
            chunk.anchor for chunk in chunks[last_start + 1 : end] if _line_total(chunk) == total
        }
        bounds = sorted({starts[i] for i in members} | {end})
        spans = {i: chunks[starts[i] : bounds[bounds.index(starts[i]) + 1]] for i in members}
        printing = [
            i
            for i in members
            if any(
                POINT_LABEL.search(chunk.text) for chunk in spans[i] if chunk.anchor not in closing
            )
        ]
        if len(printing) == len(members):
            continue
        if len(members) < 2:
            unsplit.append(first_anchor)
            continue
        absorbed.update(anchor for anchor in closing if anchor in unbuilt)
        stray = [
            anchor
            for anchor in unbuilt
            if anchor in positions and start <= positions[anchor] < end and anchor not in closing
        ]
        divides = total > 0 and total % len(members) == 0
        share = total // len(members) if divides and not printing and not stray else None
        if share is None:
            unsplit.append(first_anchor)
        for i in members:
            if i in printing:
                continue
            item, anchors = accepted[i]
            reasons = tuple(dict.fromkeys((*item.review.reasons, CHECK_POINTS_REASON)))
            review = item.review.model_copy(update={"reasons": reasons})
            updated[i] = (item.model_copy(update={"points": share, "review": review}), anchors)
    return SectionPoints(tuple(updated), tuple(unsplit), frozenset(absorbed))
