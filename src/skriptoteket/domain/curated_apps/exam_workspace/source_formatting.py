"""Copy source marks by whitespace-normalized, ordered span matching.

The model supplies structure, never typography. Matching folds whitespace only;
characters, case and punctuation remain evidence. A cursor selects repeated spans
in source order. Both the normalized index and mark projection are linear in the
source/output size. A failed paragraph may be rebuilt only from one unambiguous
source paragraph, with every gap located before any source answer is removed.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
    align_paragraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_gap_alignment import gap_spans
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    entry_unit_intervals,
    normalized_source_index,
    overlaps,
    paragraph_intervals,
    question_label_span,
    visible_intervals,
)

FORMATTING_REASON = "Formateringen kunde inte föras över"


class FormattingTransferError(ValueError):
    """No source-backed rendering can preserve the model's response structure."""


@dataclass(frozen=True)
class SourceParagraph:
    start: int
    end: int
    heading: int | None


class SourceFormatting:
    """One question's indexed source; cursors are local to each visible surface."""

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
        self.asset_positions: dict[str, list[int]] = {}
        self._asset_cursors: dict[str, int] = {}
        offset = 0
        for chunk in chunks:
            if parts:
                parts.append("\n")
                marks.append(())
                offset += 1
            for image in chunk.images:
                self.asset_positions.setdefault(image.asset_id, []).append(offset + image.offset)
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
        self.cursor = 0
        self.ignored = ignored
        self.label_span = question_label_span(
            self.text, ((p.start, p.end) for p in self.available_paragraphs), ignored
        )
        self.path = "exact"
        self.covered: set[int] = set()
        # Paragraph starts this projection consumed, and one source anchor per
        # body() input paragraph in input order; (-1, -1) means the paragraph
        # kept the model's wording without a unique source paragraph.
        self.projected: set[int] = set()
        self.entry_spans: list[tuple[int, int]] = []
        self.output_anchors: list[int] = []
        self._entry_span: tuple[int, int] = (-1, -1)

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

    def span(self, text: str) -> tuple[int, int]:
        wanted, _ = normalized_source_index(text)
        if not wanted:
            raise FormattingTransferError("empty text span")
        found = self.normalized.find(wanted, self.cursor)
        while found >= 0 and overlaps(
            self.positions[found], self.positions[found + len(wanted) - 1] + 1, self.excluded
        ):
            found = self.normalized.find(wanted, found + 1)
        if found < 0:
            raise FormattingTransferError("text differs from source")
        self.cursor = found + len(wanted)
        start, end = self.positions[found], self.positions[self.cursor - 1] + 1
        if text[0].isspace():
            while start > 0 and self.text[start - 1].isspace():
                start -= 1
        if text[-1].isspace():
            while end < len(self.text) and self.text[end].isspace():
                end += 1
        self.covered.update(range(start, end))
        if self._entry_span == (-1, -1):
            self._entry_span = (start, end)
        else:
            self._entry_span = (self._entry_span[0], end)
        return start, end

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

    def fragments(self, start: int, end: int) -> list[NativeParagraph]:
        result: list[NativeParagraph] = []
        previous_end: int | None = None
        for paragraph in self.paragraphs_in(start, end):
            left, right = max(start, paragraph.start), min(end, paragraph.end)
            if left < right:
                self.projected.add(paragraph.start)
                separator = self.text[previous_end:left] if previous_end is not None else ""
                segments = tuple(
                    segment
                    for start, end in visible_intervals(left, right, self.excluded)
                    for segment in self.text_segments(start, end)
                )
                if not segments:
                    continue
                if (
                    result
                    and previous_end is not None
                    and separator == " | "
                    and result[-1].heading_level == paragraph.heading
                ):
                    result[-1] = result[-1].model_copy(
                        update={
                            "segments": (
                                *result[-1].segments,
                                *self.text_segments(previous_end, left),
                                *segments,
                            )
                        }
                    )
                else:
                    result.append(
                        NativeParagraph(heading_level=paragraph.heading, segments=segments)
                    )
                previous_end = right
        return result

    def body(
        self,
        body: Iterable[NativeParagraph],
        *,
        answers: dict[str, tuple[str, ...]] | None = None,
    ) -> tuple[NativeParagraph, ...]:
        result: list[NativeParagraph] = []
        for paragraph in body:
            checkpoint = self.cursor
            coverage_before = self.covered.copy()
            projected_before = self.projected.copy()
            self._entry_span = (-1, -1)
            output_before = len(result)
            try:
                result.extend(self._paragraph(paragraph, answers or {}))
            except FormattingTransferError:
                self.cursor = checkpoint
                self.covered = coverage_before
                self.projected = projected_before
                aligned = self._aligned(paragraph, answers or {})
                if aligned is not None:
                    if self.path == "exact":
                        self.path = "aligned"
                    result.append(aligned)
                else:
                    self.path = "rebuilt"
                    result.extend(self._rebuild(paragraph, answers or {}))
            self.entry_spans.append(self._entry_span)
            left, right = self._entry_span
            origins = [p.start for p in self.paragraphs_in(left, right)]
            for index, output in enumerate(result[output_before:]):
                anchor = origins[min(index, len(origins) - 1)] if origins else -1
                pictures = []
                for segment in output.segments:
                    if segment.kind != "asset" or segment.asset_id not in self.asset_positions:
                        continue
                    positions = self.asset_positions[segment.asset_id]
                    ordinal = self._asset_cursors.get(segment.asset_id, 0)
                    pictures.append(positions[min(ordinal, len(positions) - 1)])
                    self._asset_cursors[segment.asset_id] = ordinal + 1
                if pictures:
                    anchor = min(pictures + ([anchor] if anchor >= 0 else []))
                self.output_anchors.append(anchor)
        return tuple(result)

    def _paragraph(
        self, paragraph: NativeParagraph, answers: dict[str, tuple[str, ...]]
    ) -> list[NativeParagraph]:
        if any(s.kind == "gap" for s in paragraph.segments) and ANSWER_LABEL.search(self.text):
            # Matching each fragment independently can steal a repeated word
            # from the question before its formatted inline-key expression.
            raise FormattingTransferError("inline key requires whole-paragraph alignment")
        result: list[NativeParagraph] = []
        pending: list[NativeSegment] = []
        heading: int | None = None
        previous_block: int | None = None
        for segment in paragraph.segments:
            if segment.kind != "text":
                pending.append(segment)
                if segment.kind == "gap":
                    self._skip_gap(answers.get(segment.gap_id, ()))
                continue
            start, end = self.span(segment.text)
            fragments = self.fragments(start, end)
            if not fragments:
                raise FormattingTransferError("span outside source paragraphs")
            for index, fragment in enumerate(fragments):
                # A source paragraph break, not the model's typography, starts a block.
                block = bisect_right(self._paragraph_ends, start) + index
                crossed = previous_block is not None and block != previous_block
                if pending and (index > 0 or crossed):
                    result.append(NativeParagraph(heading_level=heading, segments=tuple(pending)))
                    pending = []
                heading = fragment.heading_level
                pending.extend(fragment.segments)
                previous_block = block
        if pending:
            result.append(NativeParagraph(heading_level=heading, segments=tuple(pending)))
        return result

    def _skip_gap(self, answers: tuple[str, ...]) -> None:
        # Only consume an answer/blank immediately after the preceding text.
        # A separate facit answer is never searched for elsewhere in the source.
        remaining = self.normalized[self.cursor :]
        leading = len(remaining) - len(remaining.lstrip())
        shown = remaining[leading:]
        lengths = []
        for answer in answers:
            value, _ = normalized_source_index(answer)
            if (
                value
                and shown.startswith(value)
                and (len(shown) == len(value) or not shown[len(value)].isalnum())
            ):
                lengths.append(len(value))
        blank = re.match(r"_{2,}|\[\s*\]", shown)
        if blank:
            lengths.append(blank.end())
        if lengths:
            before = self.cursor
            self.cursor += leading + max(lengths)
            self.covered.update(self.positions[before : self.cursor])

    def _aligned(
        self, paragraph: NativeParagraph, answers: dict[str, tuple[str, ...]]
    ) -> NativeParagraph | None:
        text = " ".join(s.text for s in paragraph.segments if s.kind == "text")
        words = Counter(re.findall(r"\w+", text.casefold()))
        start = self.positions[self.cursor] if self.cursor < len(self.positions) else len(self.text)
        candidates = [p for p in self.available_paragraphs if p.end > start]
        scored = [
            (
                sum(
                    (
                        words & Counter(re.findall(r"\w+", self.text[p.start : p.end].casefold()))
                    ).values()
                ),
                p,
            )
            for p in candidates
        ]
        best = max((score for score, _ in scored), default=0)
        winners = [p for score, p in scored if score == best]
        if best == 0:
            plain = [p for p in winners if p.heading is None]
            winners = plain or winners
        if len(winners) != 1:
            self._entry_span = (-1, -1)
            # A source heading is formatting too: keep the model's wording only
            # when no tied winner carries marks or a heading level to lose.
            if not any(any(self.marks[p.start : p.end]) or p.heading is not None for p in winners):
                return paragraph
            return None
        source = winners[0]
        projected, lost, represented = align_paragraph(
            paragraph,
            self.text[source.start : source.end],
            self.marks[source.start : source.end],
            source.heading,
            answers,
            (self.text[source.start : self.label_span[1]],)
            if self.label_span is not None and source.start == self.label_span[0]
            else (),
        )
        if lost:
            return None
        self.projected.add(source.start)
        self._entry_span = (source.start, source.end)
        self.covered.update(source.start + index for index in represented)
        while self.cursor < len(self.positions) and self.positions[self.cursor] < source.end:
            self.cursor += 1
        return projected

    def _rebuild(
        self, paragraph: NativeParagraph, answers: dict[str, tuple[str, ...]]
    ) -> list[NativeParagraph]:
        """Rebuild a unique source paragraph, locating gaps before emitting any text.

        Token overlap selects a paragraph, not marks. Ties are refused. A sole
        remaining paragraph is also a truthful reconstruction for a wholly
        rewritten prompt. Pictures cannot be relocated by this text-only repair.
        """
        if any(s.kind == "asset" for s in paragraph.segments):
            raise FormattingTransferError("cannot rebuild picture placement")
        text = " ".join(s.text for s in paragraph.segments if s.kind == "text")
        words = Counter(re.findall(r"\w+", text.casefold()))
        source_start = (
            self.positions[self.cursor] if self.cursor < len(self.positions) else len(self.text)
        )
        candidates = [p for p in self.available_paragraphs if p.end > source_start]
        scored = [
            (
                sum(
                    (
                        words & Counter(re.findall(r"\w+", self.text[p.start : p.end].casefold()))
                    ).values()
                ),
                p,
            )
            for p in candidates
        ]
        if not scored:
            raise FormattingTransferError("no remaining source paragraph")
        best = max(score for score, _ in scored)
        winners = [p for score, p in scored if score == best]
        if len(winners) != 1 or (best < 2 and len(candidates) != 1):
            raise FormattingTransferError("ambiguous source reconstruction")
        source = winners[0]
        self.projected.add(source.start)
        self._entry_span = (source.start, source.end)
        if ANSWER_LABEL.search(self.text[source.start : source.end]):
            raise FormattingTransferError("source reconstruction would expose facit wording")
        gaps = [s for s in paragraph.segments if s.kind == "gap"]
        placements = self._gap_placements(source, gaps, answers)
        segments: list[NativeSegment] = []
        cursor = self._content_start(source)
        for left, right, gap in placements:
            segments.extend(self._rebuilt_text_segments(cursor, left))
            segments.append(gap)
            cursor = right
        segments.extend(self._rebuilt_text_segments(cursor, source.end))
        self.covered.update(range(source.start, source.end))
        if not segments:
            raise FormattingTransferError("empty reconstruction")
        while self.cursor < len(self.positions) and self.positions[self.cursor] < source.end:
            self.cursor += 1
        return [NativeParagraph(heading_level=source.heading, segments=tuple(segments))]

    def _rebuilt_text_segments(self, start: int, end: int) -> tuple[NativeTextSegment, ...]:
        return tuple(
            segment
            for left, right in visible_intervals(start, end, self.excluded)
            for segment in self.text_segments(left, right)
        )

    def _content_start(self, paragraph: SourceParagraph) -> int:
        """Skip the printed label a native field already carries, as rebuild_body does."""
        if self.label_span is not None and paragraph.start == self.label_span[0]:
            return self.label_span[1]
        return paragraph.start

    def rebuild_body(self, answers: dict[str, tuple[str, ...]]) -> tuple[NativeParagraph, ...]:
        """Recover omitted marked material only when the whole body is source-safe."""
        if ANSWER_LABEL.search(self.text):
            raise FormattingTransferError("source reconstruction would expose facit wording")
        gaps = [NativeGapSegment(gap_id=gap_id) for gap_id in answers]
        placements = self._gap_placements(SourceParagraph(0, len(self.text), None), gaps, answers)
        result: list[NativeParagraph] = []
        for paragraph in self.available_paragraphs:
            cursor = self._content_start(paragraph)
            segments: list[NativeSegment] = []
            for start, end, gap in placements:
                if paragraph.start <= start and end <= paragraph.end:
                    segments.extend(self._rebuilt_text_segments(cursor, start))
                    segments.append(gap)
                    cursor = end
                elif start < paragraph.end and end > paragraph.start:
                    raise FormattingTransferError("gap crosses source paragraph boundary")
            segments.extend(self._rebuilt_text_segments(cursor, paragraph.end))
            if segments:
                self.projected.add(paragraph.start)
                result.append(
                    NativeParagraph(heading_level=paragraph.heading, segments=tuple(segments))
                )
        if not result:
            raise FormattingTransferError("no source body to rebuild")
        self.path = "rebuilt"
        for start, end in visible_intervals(0, len(self.text), self.excluded):
            self.covered.update(range(start, end))
        return tuple(result)

    def _gap_placements(
        self,
        source: SourceParagraph,
        gaps: list[NativeGapSegment],
        answers: dict[str, tuple[str, ...]],
    ) -> list[tuple[int, int, NativeGapSegment]]:
        spans = gap_spans(self.text[source.start : source.end], gaps, answers)
        if spans is None:
            raise FormattingTransferError("gap has no unique source location")
        return [
            (source.start + span[0], source.start + span[1], gap)
            for span, gap in zip(spans, gaps, strict=True)
        ]


def formatted_text(text: str, source: SourceFormatting) -> tuple[NativeParagraph, ...]:
    return source.body(
        (NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),)
    )
