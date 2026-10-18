"""Which source chunk each emitted body paragraph shows (TASK-SKRIPT-39-04-13 D1, D9).

Source formatting projects a reply paragraph onto one question's indexed source text. This
module owns the provenance of what it emits: the chunk every source offset lies in, each
picture's own source place, and the split of an emitted paragraph wherever its source
chunk changes, so no paragraph claims content another chunk holds.
"""

from __future__ import annotations

from bisect import bisect_right

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
)


class ChunkProvenance:
    """The chunks of one indexed source, in source order, and each picture's source places."""

    def __init__(self) -> None:
        self._starts: list[int] = []
        self._anchors: list[str] = []
        self._pictures: dict[str, list[int]] = {}
        self._picture_cursors: dict[str, int] = {}

    def add(self, offset: int, chunk: DocxChunk) -> None:
        """Index ``chunk``, whose text starts at ``offset`` in the source text."""
        self._starts.append(offset)
        self._anchors.append(chunk.anchor)
        for image in chunk.images:
            self._pictures.setdefault(image.asset_id, []).append(offset + image.offset)

    def chunk_at(self, offset: int) -> str | None:
        """The anchor of the chunk holding source ``offset``; None for -1, no source place."""
        if offset < 0:
            return None
        return self._anchors[bisect_right(self._starts, offset) - 1]

    def pictures_in(self, start: int, end: int) -> list[tuple[int, str]]:
        """Every (source place, asset id) with ``start <= place < end``, sorted by place."""
        return sorted(
            (place, asset_id)
            for asset_id, places in self._pictures.items()
            for place in places
            if start <= place < end
        )

    def pieces(
        self, output: NativeParagraph, text_origin: int
    ) -> list[tuple[int, NativeParagraph]]:
        """The paragraph split where its source chunk changes, each piece with its origin.

        ``text_origin`` is the start of the one source paragraph the projection took the
        paragraph's text from, -1 when its wording has no unique source paragraph; text and
        gaps share it. A picture's origin is its own source place, its occurrences counted
        in body order. Within one chunk the earliest source place stands for the piece.
        """
        pieces: list[tuple[int, list[NativeSegment]]] = []
        for segment in output.segments:
            origin = text_origin
            if segment.kind == "asset" and segment.asset_id in self._pictures:
                places = self._pictures[segment.asset_id]
                ordinal = self._picture_cursors.get(segment.asset_id, 0)
                origin = places[min(ordinal, len(places) - 1)]
                self._picture_cursors[segment.asset_id] = ordinal + 1
            if pieces and self.chunk_at(pieces[-1][0]) == self.chunk_at(origin):
                kept, segments = pieces[-1]
                pieces[-1] = (min(kept, origin) if origin >= 0 else kept, [*segments, segment])
            else:
                pieces.append((origin, [segment]))
        return [
            (origin, output.model_copy(update={"segments": tuple(segments)}))
            for origin, segments in pieces
        ]
