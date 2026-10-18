"""Which source chunk each paragraph of a built item's body shows (review-3 N5/N6).

The body's source formatting records, for every paragraph it produced, the start of the
source paragraph that paragraph was aligned to (``SourceFormatting.output_anchors``). This
module turns those offsets into chunk anchors once, so the join of question-owned contexts
and headings, and the section placement of instructions and headings, read the alignment
and never the wording of the reply (TASK-SKRIPT-39-04-13).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    review_source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting


@dataclass(frozen=True)
class AlignedItem:
    """A built item and, per body paragraph, the anchor of the source chunk it shows.

    ``chunks[n]`` is None when body paragraph ``n`` kept the reply's wording without a
    unique source paragraph. Every change to the body states its paragraphs' chunks, so the
    two always have the same length.
    """

    item: NativeExamItem
    chunks: tuple[str | None, ...]

    def __post_init__(self) -> None:
        if len(self.chunks) != len(self.item.body):
            raise ValueError(
                f"{len(self.chunks)} aligned chunks for {len(self.item.body)} body paragraphs"
            )

    def shows(self, anchor: str) -> bool:
        """Whether a body paragraph shows the source chunk ``anchor``."""
        return anchor in self.chunks


def paragraph_chunks(source: SourceFormatting) -> tuple[str | None, ...]:
    """The chunk anchor of each paragraph of the body ``source`` last produced."""
    return tuple(source.provenance.chunk_at(offset) for offset in source.output_anchors)


def source_chunks(chunks: Sequence[DocxChunk]) -> tuple[str, ...]:
    """The chunk anchor of each paragraph of the review body, in order.

    Printed answer lines are not paragraphs of the review body (W10), so they take no
    anchor: the body ``review_source_item`` builds and this alignment always agree.
    """
    return tuple(anchor for anchor, _ in review_source_paragraphs(chunks))


def aligned_source_item(item: NativeExamItem, chunks: Sequence[DocxChunk]) -> AlignedItem:
    """An item whose body is ``chunks``' source rendering, aligned by construction.

    A body that renders no chunk is the one placeholder paragraph, which shows no chunk.
    """
    return AlignedItem(item, source_chunks(chunks) or (None,) * len(item.body))


def source_places(
    chunks: Sequence[str | None], position: Mapping[str, int], first: int
) -> list[int]:
    """Each body paragraph's source place: its aligned chunk's position.

    An unaligned paragraph takes the place of the aligned paragraph before it; with none
    before it, of the first aligned paragraph after it; with none at all, ``first``.
    """
    known = [position[c] if c is not None and c in position else None for c in chunks]
    following = next((p for p in known if p is not None), first)
    places: list[int] = []
    for place in known:
        places.append(place if place is not None else places[-1] if places else following)
    return places


# An admitted item and the anchors it holds, as a build hands it to assembly.
AcceptedEntry = tuple[AlignedItem, tuple[str, ...]]
Accepted = tuple[AcceptedEntry, ...]
