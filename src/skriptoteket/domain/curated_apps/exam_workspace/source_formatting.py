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
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_space_paragraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
    align_paragraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_gap_alignment import gap_spans
from skriptoteket.domain.curated_apps.exam_workspace.source_format_index import SourceIndex
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    normalized_source_index,
    overlaps,
    visible_intervals,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_misplaced_paragraph import (
    is_misplaced,
    rebuild_misplaced,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_paragraph_match import (
    SourceParagraph,
    overlap_scores,
)

FORMATTING_REASON = "Formateringen kunde inte föras över"


class SourceFormatting(SourceIndex):
    """One question's indexed source; cursors are local to each visible surface."""

    def __init__(
        self,
        chunks: Iterable[DocxChunk],
        *,
        ignored: tuple[str, ...] = (),
        excluded: tuple[tuple[int, int], ...] = (),
        foreign: tuple[str, ...],
    ) -> None:
        super().__init__(chunks, ignored=ignored, excluded=excluded)
        self.foreign_normalized = tuple(
            normalized_source_index(chunk_text)[0] for chunk_text in foreign
        )
        self.cursor = 0
        self.path = "exact"
        self.covered: set[int] = set()
        # Paragraph starts this projection consumed, and the source paragraph start of
        # each paragraph of the body last produced (body, rebuild_body or the coverage
        # restore); -1 means it kept the model's wording without a unique source paragraph.
        self.projected: set[int] = set()
        self.entry_spans: list[tuple[int, int]] = []
        self.output_anchors: list[int] = []
        self._entry_span: tuple[int, int] = (-1, -1)

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

    def fragments(self, start: int, end: int) -> list[NativeParagraph]:
        return [fragment for fragment, _ in self.sourced_fragments(start, end)]

    def sourced_fragments(self, start: int, end: int) -> list[tuple[NativeParagraph, int]]:
        """The visible source text in ``start``-``end`` as paragraphs, each with the start of
        the source paragraph it begins in; table cells of one row join one paragraph."""
        result: list[tuple[NativeParagraph, int]] = []
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
                    and result[-1][0].heading_level == paragraph.heading
                ):
                    joined, origin = result[-1]
                    result[-1] = (
                        joined.model_copy(
                            update={
                                "segments": (
                                    *joined.segments,
                                    *self.text_segments(previous_end, left),
                                    *segments,
                                )
                            }
                        ),
                        origin,
                    )
                else:
                    result.append(
                        (
                            NativeParagraph(heading_level=paragraph.heading, segments=segments),
                            paragraph.start,
                        )
                    )
                previous_end = right
        return result

    def body(
        self,
        body: Iterable[NativeParagraph],
        *,
        answers: dict[str, tuple[str, ...]] | None = None,
    ) -> tuple[NativeParagraph, ...]:
        """Project the reply's body; a paragraph whose text is another question's source is
        not this item's content, so it is rebuilt from this item's own source (D4)."""
        result: list[NativeParagraph] = []
        for paragraph in body:
            checkpoint = self.cursor
            coverage_before = self.covered.copy()
            projected_before = self.projected.copy()
            self._entry_span = (-1, -1)
            # Each emitted paragraph with the start of the one source paragraph its text
            # was projected from, -1 when it keeps the model's wording.
            produced: list[tuple[NativeParagraph, int]]
            try:
                produced = self._paragraph(paragraph, answers or {})
            except FormattingTransferError:
                self.cursor = checkpoint
                self.covered = coverage_before
                self.projected = projected_before
                if is_misplaced(self, paragraph):
                    produced = rebuild_misplaced(self)
                else:
                    aligned = self._aligned(paragraph, answers or {})
                    if aligned is not None:
                        if self.path == "exact":
                            self.path = "aligned"
                        produced = [(aligned, self._entry_span[0])]
                    else:
                        self.path = "rebuilt"
                        rebuilt = self._rebuild(paragraph, answers or {})
                        produced = [(output, self._entry_span[0]) for output in rebuilt]
            self.entry_spans.append(self._entry_span)
            for output, text_origin in produced:
                for origin, piece in self.provenance.pieces(output, text_origin):
                    result.append(piece)
                    self.output_anchors.append(origin)
        return tuple(result)

    def _paragraph(
        self, paragraph: NativeParagraph, answers: dict[str, tuple[str, ...]]
    ) -> list[tuple[NativeParagraph, int]]:
        if any(s.kind == "gap" for s in paragraph.segments) and ANSWER_LABEL.search(self.text):
            # Matching each fragment independently can steal a repeated word
            # from the question before its formatted inline-key expression.
            raise FormattingTransferError("inline key requires whole-paragraph alignment")
        result: list[tuple[NativeParagraph, int]] = []
        pending: list[NativeSegment] = []
        heading: int | None = None
        previous_block: int | None = None
        # Where the pending text was projected from; a new source block starts a paragraph.
        origin = -1
        for segment in paragraph.segments:
            if segment.kind != "text":
                pending.append(segment)
                if segment.kind == "gap":
                    self._skip_gap(answers.get(segment.gap_id, ()))
                continue
            start, end = self.span(segment.text)
            fragments = self.sourced_fragments(start, end)
            if not fragments:
                raise FormattingTransferError("span outside source paragraphs")
            for index, (fragment, source_start) in enumerate(fragments):
                # A source paragraph break, not the model's typography, starts a block.
                block = bisect_right(self._paragraph_ends, start) + index
                crossed = previous_block is not None and block != previous_block
                if pending and (index > 0 or crossed):
                    result.append(
                        (NativeParagraph(heading_level=heading, segments=tuple(pending)), origin)
                    )
                    pending = []
                    origin = -1
                heading = fragment.heading_level
                origin = source_start
                pending.extend(fragment.segments)
                previous_block = block
        if pending:
            result.append((NativeParagraph(heading_level=heading, segments=tuple(pending)), origin))
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
        start = self.positions[self.cursor] if self.cursor < len(self.positions) else len(self.text)
        candidates = [p for p in self.available_paragraphs if p.end > start]
        scored = overlap_scores(text, self.text, candidates)
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
        source_start = (
            self.positions[self.cursor] if self.cursor < len(self.positions) else len(self.text)
        )
        candidates = [p for p in self.available_paragraphs if p.end > source_start]
        scored = overlap_scores(text, self.text, candidates)
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
        cursor = self.content_start(source)
        for left, right, gap in placements:
            segments.extend(self.visible_text_segments(cursor, left))
            segments.append(gap)
            cursor = right
        segments.extend(self.visible_text_segments(cursor, source.end))
        self.covered.update(range(source.start, source.end))
        if not segments:
            raise FormattingTransferError("empty reconstruction")
        while self.cursor < len(self.positions) and self.positions[self.cursor] < source.end:
            self.cursor += 1
        return [NativeParagraph(heading_level=source.heading, segments=tuple(segments))]

    def rebuild_body(self, answers: dict[str, tuple[str, ...]]) -> tuple[NativeParagraph, ...]:
        """Recover omitted marked material only when the whole body is source-safe."""
        if ANSWER_LABEL.search(self.text):
            raise FormattingTransferError("source reconstruction would expose facit wording")
        gaps = [NativeGapSegment(gap_id=gap_id) for gap_id in answers]
        placements = self._gap_placements(SourceParagraph(0, len(self.text), None), gaps, answers)
        result: list[NativeParagraph] = []
        self.output_anchors = []
        for paragraph in self.available_paragraphs:
            cursor = self.content_start(paragraph)
            segments: list[NativeSegment] = []
            gap_inside = False
            for start, end, gap in placements:
                if paragraph.start <= start and end <= paragraph.end:
                    segments.extend(self.visible_text_segments(cursor, start))
                    segments.append(gap)
                    cursor = end
                    gap_inside = True
                elif start < paragraph.end and end > paragraph.start:
                    raise FormattingTransferError("gap crosses source paragraph boundary")
            if not gap_inside and is_answer_space_paragraph(
                self.text, paragraph.start, paragraph.end, self.picture_offsets
            ):
                # A gap-less printed answer line is not question text (W10); account for its
                # characters so coverage never restores it, and project no anchor for it.
                self.covered.update(range(paragraph.start, paragraph.end))
                continue
            segments.extend(self.visible_text_segments(cursor, paragraph.end))
            if segments:
                self.projected.add(paragraph.start)
                self.output_anchors.append(paragraph.start)
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
