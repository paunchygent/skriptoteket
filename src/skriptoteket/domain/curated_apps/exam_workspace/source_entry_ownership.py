"""One ownership partition over every native entry surface's source spans.

The three entry surfaces (choices, match left, match right) share one physical
source. When a paragraph, line or table cell interleaves matching entries, the
entries' spans must tile it, never overlap: a left entry may not include a right
entry's characters, and reconstructing one entry may not mark another entry's
wording as covered.

The partition is computed once for all surfaces before any wording is
projected. Printed labels establish disjoint source slots independently of
model wording. The residual entries share one ordered token-interval allocation,
including exact and rewritten neighbours. A complete earliest-ending exact walk
certifies the ordinary copy path without expanding duplicate occurrences. If
rewrites remain, whole-token edit evidence scores all residual source intervals
before the joint allocator chooses disjoint owners. An owner ends where the next
owner starts; intervening paragraphs belong to the earlier owner's continuation.
The final owner stops at source end or the next body or picture anchor.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_alignment import (
    EntryCandidate,
    assign_candidates,
    exact_candidates,
    exact_sequence,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_labels import labelled_slots
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import (
    exact_token_score,
    token_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import entry_label_end
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
    SourceFormatting,
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
    one was found before the anchor or at its unit's start.
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
    probe = SourceFormatting(chunks)
    for text in body_texts:
        try:
            start, end = probe.span(text)
        except FormattingTransferError:
            continue
        spans.append((start, end))
    return tuple(sorted(spans))


def _planned_end(
    plan: _Planned,
    following: _Planned | None,
    source_end: int,
    body_spans: tuple[tuple[int, int], ...],
) -> int:
    """Where the next owner, the question body or the source stops this one."""
    unit = (plan.unit_start, plan.unit_end)
    if following is None:
        base = source_end
    elif (following.unit_start, following.unit_end) != unit:
        # Paragraphs between two units are the earlier owner's continuation.
        base = following.unit_start
    else:
        base = following.label_start if following.label_start is not None else following.start
    for span_start, _span_end in body_spans:
        if span_start > plan.reference_end:
            return min(base, span_start)
    return base


def _planned_from_candidate(candidate: EntryCandidate, source: SourceFormatting) -> _Planned:
    start = candidate.start
    while start > candidate.unit_start and (
        source.text[start - 1].isalnum() or source.text[start - 1] == "_"
    ):
        start -= 1
    return _Planned(
        surface_index=candidate.surface_index,
        ordinal=candidate.ordinal,
        start=start,
        anchor_start=candidate.start,
        anchor_end=candidate.end,
        exact=True,
        label_start=candidate.label_start,
        unit_start=candidate.unit_start,
        unit_end=candidate.unit_end,
        reference_end=candidate.end,
    )


def plan_entry_ownership(
    chunks: tuple[DocxChunk, ...],
    surfaces: Iterable[EntrySurface],
    *,
    body_texts: Iterable[str] = (),
) -> EntryOwnership:
    """Assign every entry surface's characters to exactly one entry.

    The caller's surfaces keep their projection state for the apply step.
    Shared printed-label slots are allocated first. Residual exact and rewritten
    entries then compete in one allocation, never in independent alignments.
    """
    surface_list = tuple(surfaces)
    probes = [
        SourceFormatting(chunks, ignored=surface.source.ignored, excluded=surface.source.excluded)
        for surface in surface_list
    ]
    body_spans = _body_spans(chunks, body_texts)
    carriers = tuple(span for surface in surface_list for span in surface.source.excluded)
    labelled = (
        labelled_slots(
            probes[0],
            tuple(s.sequence for s in surface_list),
            tuple(s.texts for s in surface_list),
            (*body_spans, *carriers),
        )
        if probes
        else {}
    )
    planned: list[_Planned] = []
    for (index, ordinal), (slot, anchor) in labelled.items():
        size = entry_label_end(probes[index].text[slot.start : slot.end], ordinal) or 0
        planned.append(
            _Planned(
                surface_index=index,
                ordinal=ordinal,
                start=slot.start,
                anchor_start=anchor[0] if anchor else -1,
                anchor_end=anchor[1] if anchor else -1,
                exact=anchor is not None,
                label_start=slot.start,
                unit_start=slot.unit_start,
                unit_end=slot.unit_end,
                reference_end=anchor[1] if anchor else slot.start + size,
            )
        )
    reserved_slots = tuple((slot.start, slot.end) for slot, _ in labelled.values())
    probes = [
        SourceFormatting(
            chunks,
            ignored=s.source.ignored,
            excluded=(*s.source.excluded, *reserved_slots),
        )
        for s in surface_list
    ]
    candidates: list[EntryCandidate] = []
    pending = {
        (index, ordinal): text
        for index, surface in enumerate(surface_list)
        for ordinal, text in enumerate(surface.texts, start=1)
        if (index, ordinal) not in labelled
    }
    entry_counts = tuple(len(surface.texts) for surface in surface_list)
    blocked = (*body_spans, *carriers, *reserved_slots)
    assigned = (
        exact_sequence(probes, tuple(s.texts for s in surface_list), blocked)
        if not labelled
        else None
    )
    if assigned is None:
        for (index, ordinal), text in pending.items():
            candidates.extend(
                replace(c, evidence=exact_token_score(text))
                for c in exact_candidates(
                    probes[index], surface_list[index].sequence, index, ordinal, text
                )
            )
        assigned = assign_candidates(entry_counts, candidates, blocked=blocked)
    else:
        candidates.extend(assigned.values())
    exact_spans = {(c.surface_index, c.ordinal, c.start, c.end) for c in candidates}
    if len(assigned) < len(pending):
        # Jointly score every residual interval, including exact neighbours.
        # No entry is projected while another entry can still change its edge.
        for (index, ordinal), text in pending.items():
            candidates.extend(token_candidates(probes[index], index, ordinal, text, blocked))
        assigned = assign_candidates(entry_counts, candidates, blocked=blocked)
    unowned = [key for key in pending if key not in assigned]
    for (index, ordinal), candidate in assigned.items():
        plan = _planned_from_candidate(candidate, probes[index])
        planned.append(
            replace(
                plan,
                exact=(index, ordinal, candidate.start, candidate.end) in exact_spans,
            )
        )
    ordered = sorted(planned, key=lambda plan: (plan.start, plan.surface_index, plan.ordinal))
    seen_units: set[tuple[int, int]] = set()
    owners: list[EntryOwner] = []
    for position, plan in enumerate(ordered):
        unit = (plan.unit_start, plan.unit_end)
        first_in_unit = unit not in seen_units
        seen_units.add(unit)
        following = ordered[position + 1] if position + 1 < len(ordered) else None
        start = plan.label_start if plan.label_start is not None else plan.start
        if plan.label_start is None and first_in_unit:
            # An unlabelled entry prefix is excluded from the body before it
            # projects, so only a proven body span inside the unit precedes it.
            start = plan.unit_start
            for body_start, body_end in body_spans:
                if body_start < plan.anchor_start and body_end > start:
                    start = min(body_end, plan.anchor_start)
        end = _planned_end(plan, following, len(probes[plan.surface_index].text), body_spans)
        owners.append(
            EntryOwner(
                sequence=surface_list[plan.surface_index].sequence,
                ordinal=plan.ordinal,
                start=start,
                end=max(start, end),
                anchor_start=plan.anchor_start,
                anchor_end=plan.anchor_end,
                exact=plan.exact,
                first_in_unit=first_in_unit,
                label_start=plan.label_start,
                unit_start=plan.unit_start,
            )
        )
    for index, ordinal in unowned:
        owners.append(
            EntryOwner(
                sequence=surface_list[index].sequence,
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
