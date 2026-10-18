"""One ownership partition over every native entry surface's source spans.

The three entry surfaces (choices, match left, match right) share one physical
source. When a paragraph, line or table cell interleaves matching entries, the
entries' spans must tile it, never overlap: a left entry may not include a right
entry's characters, and reconstructing one entry may not mark another entry's
wording as covered.

One ordered token alignment assigns every entry a disjoint source interval for
all surfaces at once. This module turns those intervals into complete owners:
printed labels stay the entry's own anchor, an unlabelled first entry claims its
unit's prefix, and the unmatched gap between two owners is split at its best
sentence or clause boundary so a next entry's omitted verb stays with that
entry. Owners therefore tile the source instead of extending a predecessor to a
later entry's evidence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_alignment import (
    align_entries,
    entry_unit_bounds,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_labels import label_options
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import source_tokens
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
    SourceFormatting,
)

_SENTENCE_END = re.compile(r"[.!?…]+[\"'»”’)\]]*")
_LINE_BREAK = re.compile(r"\n")
_CLAUSE_END = re.compile(r"[,;:](?=\s|\Z)")
_CONJUNCTION_START = re.compile(
    r"(?<!\w)(?:and|but|or|nor|yet|so|men|och|eller|samt|utan|för|så|därför|dock)(?!\w)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EntrySurface:
    """One native entry surface: its produced wordings and its source index."""

    sequence: str
    texts: tuple[str, ...]
    source: SourceFormatting


@dataclass(frozen=True)
class EntryOwner:
    """One native entry's owned source span and its aligned wording anchor.

    ``start``/``end`` are the source characters the entry owns for coverage:
    its own label, its wording and its continuation paragraphs, up to the next
    owner or the next body block. ``anchor_start``/``anchor_end`` are the
    characters its wording aligned to, or ``(-1, -1)`` when alignment gave no
    evidence. ``label_start`` is the entry's own structural ordinal label when
    one was adopted.
    """

    sequence: str
    ordinal: int
    start: int
    end: int
    anchor_start: int
    anchor_end: int
    exact: bool
    first_in_unit: bool
    label_start: int | None
    unit_start: int


@dataclass(frozen=True)
class EntryOwnership:
    """The one partition every entry surface shares, plus the headings it accounts."""

    owners: tuple[EntryOwner, ...]
    heading_chunk_paragraphs: frozenset[int] = frozenset()

    def for_surface(self, sequence: str) -> tuple[EntryOwner, ...]:
        """The surface's owners in rendered ordinal order, one per entry."""
        return tuple(
            sorted(
                (owner for owner in self.owners if owner.sequence == sequence),
                key=lambda owner: owner.ordinal,
            )
        )

    def exclusion_ranges(self) -> tuple[tuple[int, int], ...]:
        """The source spans entry surfaces own; the question body must exclude them."""
        merged: list[list[int]] = []
        for owner in sorted(self.owners, key=lambda owner: owner.start):
            if owner.start < 0 or owner.end <= owner.start:
                continue
            if merged and owner.start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], owner.end)
            else:
                merged.append([owner.start, owner.end])
        return tuple((start, end) for start, end in merged)


def produced_entry_body(text: str) -> tuple[NativeParagraph, ...]:
    """One produced entry wording as an unmarked paragraph before projection."""
    return (
        NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
    )


@dataclass(frozen=True)
class _Planned:
    surface_index: int
    ordinal: int
    start: int
    anchor_start: int
    anchor_end: int
    exact: bool
    label_start: int | None
    unit_start: int
    unit_end: int
    reference_end: int


def _heading_chunk_paragraphs(chunks: tuple[DocxChunk, ...]) -> frozenset[int]:
    """The source paragraph starts an assembly-placed heading chunk already covers."""
    starts: set[int] = set()
    offset = 0
    for index, chunk in enumerate(chunks):
        if index:
            offset += 1
        if chunk.kind == "heading":
            starts.update(offset + paragraph.offset for paragraph in chunk.paragraphs)
        offset += len(chunk.text)
    return frozenset(starts)


def _body_spans(
    chunks: tuple[DocxChunk, ...], body_texts: Iterable[str]
) -> tuple[tuple[int, int], ...]:
    """The source spans the question body owns: its exact wording and its pictures."""
    spans: list[tuple[int, int]] = []
    offset = 0
    for index, chunk in enumerate(chunks):
        if index:
            offset += 1
        spans.extend((offset + image.offset, offset + image.offset) for image in chunk.images)
        offset += len(chunk.text)
    probe = SourceFormatting(chunks, foreign=())
    for text in body_texts:
        try:
            start, end = probe.span(text)
        except FormattingTransferError:
            continue
        spans.append((start, end))
    return tuple(sorted(spans))


def _last_sentence_break(text: str, gap_start: int, gap_end: int) -> int | None:
    """The last completed sentence or physical line inside the unmatched gap."""
    found: int | None = None
    for match in _SENTENCE_END.finditer(text, gap_start, gap_end):
        end = match.end()
        if end < len(text) and not text[end].isspace() and end != gap_end:
            continue
        found = end
    for match in _LINE_BREAK.finditer(text, gap_start, gap_end):
        end = match.end()
        found = end if found is None else max(found, end)
    return found


def _last_clause_break(text: str, gap_start: int, gap_end: int) -> int | None:
    """The last clause boundary: punctuation end or a leading conjunction."""
    found: int | None = None
    for match in _CLAUSE_END.finditer(text, gap_start, gap_end):
        found = match.end() if found is None else max(found, match.end())
    for match in _CONJUNCTION_START.finditer(text, gap_start, gap_end):
        found = match.start() if found is None else max(found, match.start())
    return found


def _split_gap(
    text: str,
    gap_start: int,
    gap_end: int,
    following_label_start: int | None,
    body_spans: tuple[tuple[int, int], ...],
) -> int:
    """Split an unmatched gap so the next entry keeps its own omitted prefix.

    A printed label is a hard boundary. Otherwise the latest completed sentence
    or line inside the gap wins, then the latest clause boundary, and a gap with
    neither belongs to the following entry, never to the predecessor's wording:
    the next entry's omitted verb must not be reconstructed as the previous
    entry's tail.
    """
    if gap_end <= gap_start:
        return gap_start
    if following_label_start is not None and gap_start <= following_label_start <= gap_end:
        boundary = following_label_start
    else:
        found = _last_sentence_break(text, gap_start, gap_end)
        if found is None:
            found = _last_clause_break(text, gap_start, gap_end)
        boundary = gap_start if found is None else found
    for span_start, _span_end in body_spans:
        if gap_start < span_start < boundary:
            boundary = span_start
    return max(gap_start, min(boundary, gap_end))


def _stop_before_body(
    base: int, reference_end: int, body_spans: tuple[tuple[int, int], ...]
) -> int:
    """An owner never extends past the question body that follows its wording."""
    for span_start, _span_end in body_spans:
        if span_start > reference_end:
            return min(base, span_start)
    return base


def plan_entry_ownership(
    chunks: tuple[DocxChunk, ...],
    surfaces: Iterable[EntrySurface],
    *,
    body_texts: Iterable[str] = (),
) -> EntryOwnership:
    """Assign every entry surface's characters to exactly one entry.

    The caller's surfaces keep their projection state for the apply step. One
    ordered token alignment assigns every surface's entries disjoint intervals;
    the owner sweep then extends each interval to complete sentence or clause
    content without crossing the next owner.
    """
    surface_list = tuple(surfaces)
    probes = [
        SourceFormatting(
            chunks,
            ignored=surface.source.ignored,
            excluded=surface.source.excluded,
            foreign=(),
        )
        for surface in surface_list
    ]
    body_spans = _body_spans(chunks, body_texts)
    text = probes[0].text if probes else ""
    sequences = tuple(surface.sequence for surface in surface_list)
    texts = tuple(surface.texts for surface in surface_list)
    labels = label_options(text, sequences, texts, source_tokens(text), blocked=body_spans)
    anchors = align_entries(text, sequences, texts, labels=labels, blocked=body_spans)
    planned: list[_Planned] = []
    unowned: list[tuple[int, int]] = []
    for index, surface in enumerate(surface_list):
        for ordinal in range(1, len(surface.texts) + 1):
            anchor = anchors.get((index, ordinal))
            if anchor is None:
                unowned.append((index, ordinal))
                continue
            unit_start, unit_end = entry_unit_bounds(probes[index], anchor.start)
            planned.append(
                _Planned(
                    surface_index=index,
                    ordinal=ordinal,
                    start=anchor.start,
                    anchor_start=anchor.anchor_start,
                    anchor_end=anchor.anchor_end,
                    exact=anchor.exact,
                    label_start=anchor.label_start,
                    unit_start=unit_start,
                    unit_end=unit_end,
                    reference_end=anchor.anchor_end if anchor.anchor_end >= 0 else anchor.end,
                )
            )
    ordered = sorted(planned, key=lambda plan: (plan.start, plan.surface_index, plan.ordinal))
    seen_units: set[tuple[int, int]] = set()
    owners: list[EntryOwner] = []
    previous_end = 0
    for position, plan in enumerate(ordered):
        unit = (plan.unit_start, plan.unit_end)
        first_in_unit = unit not in seen_units
        seen_units.add(unit)
        following = ordered[position + 1] if position + 1 < len(ordered) else None
        if plan.label_start is not None:
            start = plan.label_start
        elif first_in_unit:
            start = plan.unit_start
            for span_start, span_end in body_spans:
                if span_start < plan.start and span_end > start:
                    start = min(span_end, plan.start)
        else:
            start = previous_end
            for span_start, span_end in body_spans:
                if previous_end <= span_start and span_end <= plan.start:
                    start = max(start, span_end)
        start = max(0, start, previous_end)
        if plan.label_start is None and first_in_unit:
            start = min(start, plan.start)
        if following is None:
            end = _stop_before_body(len(text), plan.reference_end, body_spans)
        elif following.label_start is not None:
            end = _stop_before_body(following.label_start, plan.reference_end, body_spans)
        elif (
            following.unit_start,
            following.unit_end,
        ) != unit and following.unit_start >= plan.reference_end:
            end = _stop_before_body(following.unit_start, plan.reference_end, body_spans)
        else:
            end = _split_gap(
                text,
                plan.reference_end,
                max(following.start, plan.reference_end),
                following.label_start,
                body_spans,
            )
        end = max(end, start, plan.reference_end)
        owners.append(
            EntryOwner(
                sequence=sequences[plan.surface_index],
                ordinal=plan.ordinal,
                start=start,
                end=end,
                anchor_start=plan.anchor_start,
                anchor_end=plan.anchor_end,
                exact=plan.exact,
                first_in_unit=first_in_unit,
                label_start=plan.label_start,
                unit_start=plan.unit_start,
            )
        )
        previous_end = end
    for index, ordinal in unowned:
        owners.append(
            EntryOwner(
                sequence=sequences[index],
                ordinal=ordinal,
                start=-1,
                end=-1,
                anchor_start=-1,
                anchor_end=-1,
                exact=False,
                first_in_unit=False,
                label_start=None,
                unit_start=-1,
            )
        )
    owners.sort(key=lambda owner: (owner.sequence, owner.ordinal))
    return EntryOwnership(tuple(owners), _heading_chunk_paragraphs(chunks))
