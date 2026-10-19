"""One question's indexed source and its read-only lookups; projection state lives
in SourceFormatting."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    entry_unit_intervals,
    normalized_source_index,
    paragraph_intervals,
    question_label_span,
    visible_intervals,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_paragraph_match import (
    SourceParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_provenance import ChunkProvenance


class SourceIndex:
    """One question's chunks indexed as text, marks, paragraphs and normalized positions."""

    def __init__(
        self,
        chunks: Iterable[DocxChunk],
        *,
        ignored: tuple[str, ...] = (),
        excluded: tuple[tuple[int, int], ...] = (),
    ) -> None:
        parts: list[str] = []
        marks: list[tuple[str, ...]] = []
        paragraphs: list[SourceParagraph] = []
        self.provenance = ChunkProvenance()
        offset = 0
        for chunk in chunks:
            if parts:
                parts.append("\n")
                marks.append(())
                offset += 1
            self.provenance.add(offset, chunk)
            parts.append(chunk.text)
            chunk_marks: list[tuple[str, ...]] = [()] * len(chunk.text)
            for run in chunk.runs:
                chunk_marks[run.offset : run.offset + len(run.text)] = [run.marks] * len(run.text)
            marks.extend(chunk_marks)
            if chunk.paragraphs:
                paragraphs.extend(
                    SourceParagraph(
                        offset + p.offset, offset + p.offset + len(p.text), p.heading_level
                    )
                    for p in chunk.paragraphs
                )
            elif chunk.text:
                paragraphs.append(SourceParagraph(offset, offset + len(chunk.text), None))
            offset += len(chunk.text)
        self.text = "".join(parts)
        self.marks = marks
        self.paragraphs = paragraphs
        # Absolute source offsets of this source's pictures, for the W10 answer-space rule.
        self.picture_offsets = tuple(
            place for place, _ in self.provenance.pictures_in(0, len(self.text))
        )
        self.entry_units = [
            SourceParagraph(*unit)
            for unit in entry_unit_intervals(
                self.text, ((p.start, p.end, p.heading) for p in paragraphs)
            )
        ]
        self._entry_unit_ends = [unit.end for unit in self.entry_units]
        self.excluded = excluded
        self.available_paragraphs = [
            SourceParagraph(start, end, heading)
            for start, end, heading in paragraph_intervals(
                ((p.start, p.end, p.heading) for p in paragraphs), excluded, len(self.text)
            )
        ]
        self._paragraph_ends = [p.end for p in paragraphs]
        self.normalized, self.positions = normalized_source_index(self.text)
        self.ignored = ignored
        self.label_span = question_label_span(
            self.text, ((p.start, p.end) for p in self.available_paragraphs), ignored
        )

    def entry_unit_at(self, offset: int) -> SourceParagraph | None:
        """Locate an indexed paragraph/line/table-cell envelope in logarithmic time."""
        index = bisect_right(self._entry_unit_ends, offset)
        if index >= len(self.entry_units):
            return None
        unit = self.entry_units[index]
        return unit if unit.start <= offset < unit.end else None

    def paragraphs_in(self, start: int, end: int) -> Iterable[SourceParagraph]:
        """Visit only overlapping paragraphs, without copying the remaining index."""
        index = bisect_right(self._paragraph_ends, start)
        while index < len(self.paragraphs) and self.paragraphs[index].start < end:
            yield self.paragraphs[index]
            index += 1

    def paragraph_at(self, offset: int) -> SourceParagraph | None:
        """The source paragraph holding ``offset``, or None inside a separator."""
        index = bisect_right(self._paragraph_ends, offset)
        if index >= len(self.paragraphs):
            return None
        paragraph = self.paragraphs[index]
        return paragraph if paragraph.start <= offset < paragraph.end else None

    def text_segments(self, start: int, end: int) -> tuple[NativeTextSegment, ...]:
        """Split only at source mark changes; no model-selected style enters storage."""
        result: list[NativeTextSegment] = []
        at = start
        while at < end:
            finish = at + 1
            while finish < end and self.marks[finish] == self.marks[at]:
                finish += 1
            result.append(NativeTextSegment(text=self.text[at:finish], marks=self.marks[at]))
            at = finish
        return tuple(result)

    def visible_text_segments(self, start: int, end: int) -> tuple[NativeTextSegment, ...]:
        return tuple(
            segment
            for left, right in visible_intervals(start, end, self.excluded)
            for segment in self.text_segments(left, right)
        )

    def content_start(self, paragraph: SourceParagraph) -> int:
        """Skip the printed label a native field already carries, as rebuild_body does."""
        if self.label_span is not None and paragraph.start == self.label_span[0]:
            return self.label_span[1]
        return paragraph.start
