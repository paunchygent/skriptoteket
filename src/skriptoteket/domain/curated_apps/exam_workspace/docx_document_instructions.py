"""Own the document-level instructions of an assembled exam.

This module decides which source chunks section placement never uses (exam-wide text, exam
metadata and the printed totals the points plan classifies as metadata), narrows every
instruction to the chunks placement may use, publishes each exam-wide chunk once from its own
source text, and builds the document's global instructions from the instructions no item or
parent holds. Every rule is structural: it follows the anchors the grouping and the points
plan classified, never the wording of a line.
"""

from collections.abc import Iterable, Mapping

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
    source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatted_instructions import (
    instruction_paragraphs,
)


def placement_exclusions(
    exam_wide: frozenset[str], exam_metadata: frozenset[str], printed_metadata: frozenset[str]
) -> frozenset[str]:
    """The anchors no section placement uses: they open, join and end no run.

    Exam-wide text renders once at document scope (``exam_wide_instructions``); exam metadata
    and a printed total the points plan classifies as metadata render nowhere as exam text.
    """
    return exam_wide | exam_metadata | printed_metadata


def placement_chunks(
    chunks: tuple[DocxChunk, ...],
    excluded: frozenset[str],
    accepted: Iterable[tuple[NativeExamItem, tuple[str, ...]]],
) -> tuple[DocxChunk, ...]:
    """The chunks section placement scans: every chunk outside ``excluded``.

    An excluded chunk an accepted item holds stays, because it is that item's own chunk and
    placement positions the item by its own chunks; it is placed under the rules for an
    item's own chunk. No other excluded chunk opens, joins or ends a run.
    """
    held = {anchor for _, anchors in accepted for anchor in anchors}
    return tuple(c for c in chunks if c.anchor not in excluded or c.anchor in held)


def exam_wide_instructions(
    chunks: tuple[DocxChunk, ...],
    exam_wide: frozenset[str],
    exam_metadata: frozenset[str],
    printed_metadata: frozenset[str],
) -> tuple[ProducedMetadata, ...]:
    """Each exam-wide chunk with text as an instruction of its own source text.

    No batch claims an exam-wide chunk, so its placement never depends on a reply. Exam
    metadata and a printed total the points plan classifies as metadata go nowhere.
    """
    return tuple(
        ProducedMetadata(text=chunk.text, source_anchors=(chunk.anchor,))
        for chunk in chunks
        if chunk.anchor in exam_wide
        and chunk.anchor not in exam_metadata
        and chunk.anchor not in printed_metadata
        and chunk.text
    )


def without_excluded(
    instructions: Iterable[ProducedMetadata],
    excluded: frozenset[str],
    by_anchor: Mapping[str, DocxChunk],
) -> tuple[ProducedMetadata, ...]:
    """Each instruction narrowed to its anchors outside ``excluded``, before placement.

    A narrowed instruction shows the source text of the chunks it keeps; one left with no
    anchors is dropped. Its remaining content then goes through normal placement.
    """
    narrowed: list[ProducedMetadata] = []
    for instruction in instructions:
        kept = tuple(a for a in instruction.source_anchors if a not in excluded)
        if kept == instruction.source_anchors:
            narrowed.append(instruction)
        elif kept:
            text = body_plain_text(source_paragraphs(by_anchor[a] for a in kept))
            narrowed.append(ProducedMetadata(text=text, source_anchors=kept))
    return tuple(narrowed)


def global_instructions(
    chunks: tuple[DocxChunk, ...],
    unplaced: tuple[ProducedMetadata, ...],
    exam_wide: tuple[ProducedMetadata, ...],
    by_anchor: Mapping[str, DocxChunk],
) -> tuple[NativeParagraph, ...]:
    """The document's instructions: every unplaced instruction and the exam-wide text.

    With exam-wide text, each instruction shows once by its anchors, in the order of its
    first source chunk.
    """
    published = _in_source_order(chunks, (*unplaced, *exam_wide)) if exam_wide else unplaced
    return tuple(
        paragraph
        for instruction in published
        for paragraph in instruction_paragraphs(instruction, by_anchor)
    )


def _in_source_order(
    chunks: tuple[DocxChunk, ...], instructions: tuple[ProducedMetadata, ...]
) -> tuple[ProducedMetadata, ...]:
    """Each instruction once by its anchors, in the order of its first source chunk."""
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    ordered = sorted(
        instructions,
        key=lambda i: min((positions.get(a, len(positions)) for a in i.source_anchors), default=0),
    )
    seen: set[str] = set()
    unique = []
    for instruction in ordered:
        anchors = set(instruction.source_anchors)
        if anchors and anchors <= seen:
            continue
        seen |= anchors
        unique.append(instruction)
    return tuple(unique)
