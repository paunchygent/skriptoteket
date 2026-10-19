"""Build a gap_fill body paragraph from its own source paragraph (TASK-SKRIPT-39-04-16).

A gap_fill body paragraph aligned to a source paragraph with blank runs is rebuilt from
that source paragraph: its visible source text, starting after the printed question label
and ending before an inline answer label, with the reply's gaps filling the blank runs in
source order. A paragraph with no blank run before its inline answer label has one blank
run at the label's place (TASK-SKRIPT-39-04-17). The reply supplies only its gaps and
their accepted values; its wording is discarded, never compared. A gap count that differs
from the blank-run count raises ``GapCountMismatchError``, which is not a
``FormattingTransferError``, so the whole-body rebuild never runs for a count mismatch.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_index import (
    SourceIndex,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    visible_intervals,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_paragraph_match import (
    SourceParagraph,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
        SourceFormatting,
    )

_UNDERSCORE_RUN = re.compile(r"_{2,}")
_DOT_RUN = re.compile(r"[.…]+")


class GapCountMismatchError(ValueError):
    """A gap paragraph's reply gaps do not fill its source blank runs one to one."""

    def __init__(self, gaps: int, blanks: int) -> None:
        super().__init__(f"{gaps} gaps for {blanks} blank runs")
        self.gaps = gaps
        self.blanks = blanks

    @property
    def reason(self) -> str:
        """The teacher's review reason, inflected by count (user decision 2026-10-18)."""
        gaps = f"{self.gaps} {'lucka' if self.gaps == 1 else 'luckor'}"
        blanks = f"{self.blanks} {'tom svarsrad' if self.blanks == 1 else 'tomma svarsrader'}"
        return f"Frågan följer inte provformatet: {gaps} men {blanks}."


def blank_runs(text: str) -> list[tuple[int, int]]:
    """One paragraph's blank runs by character class, never by letter content (D3).

    Any run of two or more underscores makes exactly those runs the blanks. Otherwise an
    ellipsis or a run of two or more dots counts only when no letter touches it, so a
    letter hint such as ``(s…t)`` is not a blank.
    """
    underscores = [(match.start(), match.end()) for match in _UNDERSCORE_RUN.finditer(text)]
    if underscores:
        return underscores
    result: list[tuple[int, int]] = []
    for match in _DOT_RUN.finditer(text):
        start, end = match.span()
        if "…" not in match.group() and end - start < 2:
            continue
        if start > 0 and text[start - 1].isalpha():
            continue
        if end < len(text) and text[end].isalpha():
            continue
        result.append((start, end))
    return result


@dataclass(frozen=True)
class _GapUnit:
    """One source paragraph with blank runs, extended over its table row."""

    anchor: int
    start: int
    end: int
    source_end: int
    heading: int | None
    blank_runs: tuple[tuple[int, int], ...]


def _joins_row(text: str, left: SourceParagraph, right: SourceParagraph) -> bool:
    return left.heading == right.heading and text[left.end : right.start] == " | "


def _source_unit(source: SourceFormatting, anchor: int) -> tuple[SourceParagraph, ...] | None:
    """The source paragraph holding ``anchor``, extended over the cells of its table row."""
    paragraph = source.paragraph_at(anchor)
    if paragraph is None:
        return None
    index = source.paragraphs.index(paragraph)
    first = index
    while first > 0 and _joins_row(
        source.text, source.paragraphs[first - 1], source.paragraphs[first]
    ):
        first -= 1
    last = index
    while last + 1 < len(source.paragraphs) and _joins_row(
        source.text, source.paragraphs[last], source.paragraphs[last + 1]
    ):
        last += 1
    return tuple(source.paragraphs[first : last + 1])


def _answer_label_cut(source: SourceFormatting, start: int, end: int) -> int | None:
    """Cut the build span at the first inline answer label, with any wrapper ``(``.

    Returns None when no answer label stands in the span, so the caller keeps the
    unit's end.
    """
    label = ANSWER_LABEL.search(source.text, start, end)
    if label is None:
        return None
    opening = source.text.rfind("(", start, label.start())
    if opening >= start and not source.text[opening + 1 : label.start()].strip():
        return opening
    return label.start()


def _unit_blank_runs(
    source: SourceFormatting,
    unit: tuple[SourceParagraph, ...],
    start: int,
    end: int,
) -> list[tuple[int, int]]:
    """The whole unit's blank runs, in source order, inside the visible build span.

    The blank-class choice is made once over the whole D2 source unit: the unit's cells
    are joined by exactly " | " (checked by _joins_row), which holds no "_", "." or "…"
    and no letter, so every per-cell letter-adjacency decision stays the same.
    """
    visible = visible_intervals(start, end, source.excluded)
    result: list[tuple[int, int]] = []
    for left, right in blank_runs(source.text[unit[0].start : unit[-1].end]):
        run_start, run_end = unit[0].start + left, unit[0].start + right
        if run_start < start or run_end > end:
            continue
        if not any(
            visible_start <= run_start and run_end <= visible_end
            for visible_start, visible_end in visible
        ):
            continue
        result.append((run_start, run_end))
    return result


def _gap_unit(source: SourceFormatting, anchor: int) -> _GapUnit | None:
    """One source paragraph's build span with its blank runs, if it has any to fill.

    A span with no blank run before its inline answer label still has one blank run:
    a zero-width run at the label's place, so the paragraph is built from its source
    text up to the label. A span with neither a blank run nor an answer label has no
    unit, and the reply's rendering is kept.
    """
    if anchor < 0:
        return None
    unit = _source_unit(source, anchor)
    if unit is None:
        return None
    start = source.content_start(unit[0])
    cut = _answer_label_cut(source, start, unit[-1].end)
    end = unit[-1].end if cut is None else cut
    runs = _unit_blank_runs(source, unit, start, end)
    if not runs:
        if cut is None:
            return None
        runs = [(cut, cut)]
    return _GapUnit(unit[0].start, start, end, unit[-1].end, unit[0].heading, tuple(runs))


def _trim_light_edges(segments: list[NativeSegment]) -> list[NativeSegment]:
    """Trim the paragraph's own first and last text segment, dropping either if empty.

    Only a text segment that stands first is stripped on its left, and only one that stands
    last on its right. A gap or a picture at either edge is not a text segment, so the space
    that separates it from the text beside it is kept.
    """
    if segments and isinstance(segments[0], NativeTextSegment):
        text = segments[0].text.lstrip()
        if text:
            segments[0] = NativeTextSegment(text=text, marks=segments[0].marks)
        else:
            segments.pop(0)
    if segments and isinstance(segments[-1], NativeTextSegment):
        text = segments[-1].text.rstrip()
        if text:
            segments[-1] = NativeTextSegment(text=text, marks=segments[-1].marks)
        else:
            segments.pop()
    return segments


def source_paragraph(
    source: SourceIndex,
    start: int,
    end: int,
    heading: int | None,
    runs: Sequence[tuple[int, int]] = (),
    gaps: Sequence[NativeGapSegment] = (),
    pictures: Sequence[tuple[int, str]] = (),
) -> NativeParagraph:
    """Build one paragraph from a source span, with each gap in its blank run (2g).

    ``runs`` and ``gaps`` line up one to one; the caller checks their lengths. ``pictures``
    are (source place, asset id), sorted, and each is emitted at its place: a place before
    ``start`` stands at ``start``, a place after ``end`` at ``end``, and a place inside a
    text stretch splits the text there. A picture at a blank run's start stands before the
    gap. A source line break stays inside its text segment, as ``sourced_fragments`` renders
    it, so the span's source paragraph stays one paragraph. With no runs, no gaps and no
    pictures the plain source paragraph text is returned. An excluded interval removed
    inside the span never leaves two spaces at its join (TASK-SKRIPT-39-04-15 D5).
    """
    segments: list[NativeSegment] = []
    cursor = start
    placed = [(min(max(place, start), end), asset_id) for place, asset_id in pictures]
    index = 0

    def text_until(target: int) -> None:
        nonlocal cursor
        if target > cursor:
            for segment in source.visible_text_segments(cursor, target):
                if (
                    segments
                    and isinstance(segments[-1], NativeTextSegment)
                    and segments[-1].text[-1:].isspace()
                    and segment.text[:1].isspace()
                ):
                    segments[-1] = segments[-1].model_copy(
                        update={"text": segments[-1].text.rstrip()}
                    )
                segments.append(segment)
            cursor = target

    for (run_start, run_end), gap in zip(runs, gaps, strict=True):
        while index < len(placed) and placed[index][0] < run_start:
            text_until(placed[index][0])
            segments.append(NativeAssetSegment(asset_id=placed[index][1]))
            index += 1
        while index < len(placed) and placed[index][0] == run_start:
            text_until(run_start)
            segments.append(NativeAssetSegment(asset_id=placed[index][1]))
            index += 1
        text_until(run_start)
        segments.append(gap)
        cursor = run_end
    while index < len(placed):
        text_until(placed[index][0])
        segments.append(NativeAssetSegment(asset_id=placed[index][1]))
        index += 1
    text_until(end)
    return NativeParagraph(heading_level=heading, segments=tuple(_trim_light_edges(segments)))


def gap_paragraphs_from_source(
    source: SourceFormatting, body: tuple[NativeParagraph, ...]
) -> tuple[NativeParagraph, ...]:
    """Replace each blank-run unit's reply paragraphs with one paragraph built from source.

    Paragraphs aligned to no source paragraph, or to a source paragraph without blank
    runs, keep their projection. One built paragraph stands at the place of the unit's
    first reply paragraph; the other reply paragraphs of that unit are removed.
    """
    anchors = list(source.output_anchors)
    units = [_gap_unit(source, anchor) for anchor in anchors]
    grouped: dict[tuple[int, int], list[int]] = {}
    for index, unit in enumerate(units):
        if unit is not None:
            grouped.setdefault((unit.anchor, unit.end), []).append(index)
    result: list[NativeParagraph] = []
    result_anchors: list[int] = []
    for index, (anchor, paragraph) in enumerate(zip(anchors, body, strict=True)):
        unit = units[index]
        if unit is None:
            result.append(paragraph)
            result_anchors.append(anchor)
            continue
        members = grouped[(unit.anchor, unit.end)]
        if members[0] != index:
            continue
        pictures = source.provenance.pictures_in(unit.anchor, unit.source_end)
        reply_pictures = Counter(
            segment.asset_id
            for member in members
            for segment in body[member].segments
            if segment.kind == "asset"
        )
        if reply_pictures != Counter(asset_id for _, asset_id in pictures):
            raise FormattingTransferError("cannot rebuild picture placement")
        gaps = [
            segment
            for member in members
            for segment in body[member].segments
            if segment.kind == "gap"
        ]
        if len(gaps) != len(unit.blank_runs):
            raise GapCountMismatchError(len(gaps), len(unit.blank_runs))
        result.append(
            source_paragraph(
                source,
                unit.start,
                unit.end,
                unit.heading,
                unit.blank_runs,
                gaps,
                pictures,
            )
        )
        result_anchors.append(unit.anchor)
    source.output_anchors = result_anchors
    return tuple(result)
