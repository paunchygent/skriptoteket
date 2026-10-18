"""Which source chunk each paragraph of a built item's body shows (review-3 N5/N6).

The body's source formatting records, for every paragraph it produced, the start of the
source paragraph that paragraph was aligned to (``SourceFormatting.output_anchors``). This
module turns those offsets into chunk anchors once, so the join of question-owned contexts
and headings reads the alignment and never the wording of the reply.
"""

from bisect import bisect_right
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting


@dataclass(frozen=True)
class AlignedItem:
    """A built item and, per body paragraph, the anchor of the source chunk it shows.

    ``chunks[n]`` is None when body paragraph ``n`` kept the reply's wording without a
    unique source paragraph.
    """

    item: NativeExamItem
    chunks: tuple[str | None, ...]


def paragraph_chunks(source: SourceFormatting) -> tuple[str | None, ...]:
    """The chunk anchor of each paragraph of the body ``source`` last produced."""
    starts = [start for start, _ in source.chunk_starts]
    return tuple(
        source.chunk_starts[bisect_right(starts, offset) - 1][1] if offset >= 0 else None
        for offset in source.output_anchors
    )
