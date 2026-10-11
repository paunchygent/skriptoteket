"""Equal split of a printed section total over the section's items that print no points."""

import re

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItem

AcceptedItem = tuple[NativeExamItem, tuple[str, ...]]


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
    if len(labels) != 1:
        return None
    number = re.search(r"\d+", labels[0])
    return int(number.group()) if number else None


def split_section_totals(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[AcceptedItem, ...],
    instructions: tuple[ProducedMetadata, ...],
    unbuilt: frozenset[str],
) -> tuple[tuple[AcceptedItem, ...], tuple[str, ...]]:
    """Give each item in a section an equal share of the section's printed total.

    A section starts at an instruction that prints a total, or at a section heading whose
    one printed total the model left out, and runs to the next such
    instruction or to the end of the document. The total is split only when the section has
    at least two members, every member prints no points, no source chunk in the section
    went unbuilt, and the total divides evenly over the members. A total over one question
    is that question's own printed points misread as a section total, so it stays unsplit.
    Sections whose members all print points, or that have no members, need no split; every
    other section left unsplit is reported by its first anchor.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    totals = [(instruction, _total(instruction, chunks, positions)) for instruction in instructions]
    sections = sorted(
        (positions[first], first, total)
        for instruction, total in totals
        if total is not None
        for first in (min(instruction.source_anchors, key=positions.__getitem__),)
    )
    starts = [min(positions[anchor] for anchor in anchors) for _, anchors in accepted]
    unbuilt_positions = [positions[anchor] for anchor in unbuilt if anchor in positions]
    updated = list(accepted)
    unsplit: list[str] = []
    for index, (start, first_anchor, total) in enumerate(sections):
        end = sections[index + 1][0] if index + 1 < len(sections) else len(chunks)
        members = [i for i, position in enumerate(starts) if start <= position < end]
        if all(accepted[i][0].points is not None for i in members):
            continue
        if (
            total <= 0
            or len(members) < 2
            or total % len(members) != 0
            or any(accepted[i][0].points is not None for i in members)
            or any(start <= position < end for position in unbuilt_positions)
        ):
            unsplit.append(first_anchor)
            continue
        share = total // len(members)
        for i in members:
            item, anchors = accepted[i]
            updated[i] = (item.model_copy(update={"points": share}), anchors)
    return tuple(updated), tuple(unsplit)
