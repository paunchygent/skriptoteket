"""Assign source slots jointly without enumerating occurrence combinations.

Printed-label slots are assigned before wording projection. If the entries'
individually best slots form a disjoint ordered allocation, their union is the
global optimum and needs no search. Ambiguous allocations use ordered dynamic
programming; at equal evidence and preference only the earliest ending slot
can matter, because it leaves every later suffix available. This dominance
rule removes redundant occurrence transitions without capping or discarding
supported source text. Unlabelled exact occurrences use the same assignment.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    entry_label_end,
    entry_source_extent,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting


@dataclass(frozen=True)
class EntryCandidate:
    """One exact occurrence of one produced wording, with its structural evidence."""

    surface_index: int
    ordinal: int
    start: int
    end: int
    unit_start: int
    unit_end: int
    label_start: int | None
    preference: int
    evidence: int = 0


def entry_unit_bounds(source: SourceFormatting, start: int) -> tuple[int, int]:
    """The entry's paragraph, physical line or table cell envelope."""
    return entry_source_extent(
        source, NativeSourceEntry("", 1, start, min(start + 1, len(source.text)))
    )


def entry_label_start(
    source: SourceFormatting, unit_start: int, anchor_start: int, ordinal: int
) -> int | None:
    """The closest structural ordinal label before the anchor, if one exists."""
    found: int | None = None
    for candidate in range(unit_start, anchor_start):
        if candidate > unit_start and not source.text[candidate - 1].isspace():
            continue
        if entry_label_end(source.text[candidate:anchor_start], ordinal) is not None:
            found = candidate
    return found


def entry_unit_labels(
    source: SourceFormatting, unit_start: int, unit_end: int, ordinal: int
) -> tuple[tuple[int, int], ...]:
    """Every structural ordinal label in the unit, with the size it spans."""
    labels: list[tuple[int, int]] = []
    for candidate in range(unit_start, unit_end):
        if candidate > unit_start and not source.text[candidate - 1].isspace():
            continue
        size = entry_label_end(source.text[candidate:unit_end], ordinal)
        if size is not None:
            labels.append((candidate, size))
    return tuple(labels)


def _folded(text: str) -> str:
    return SourceFormatting((DocxChunk("fold", "paragraph", text, text),)).normalized


def _label_preference(sequence: str, source: SourceFormatting, label_start: int | None) -> int:
    """A soft label-family preference; source order still assigns other layouts."""
    if label_start is None:
        return 2
    at = label_start
    while at < len(source.text) and source.text[at].isspace():
        at += 1
    if at < len(source.text) and source.text[at] in "([{":
        at += 1
    token = source.text[at] if at < len(source.text) else ""
    if sequence == "match_left":
        return 0 if token.isdigit() else 1
    if sequence == "match_right":
        return 0 if token.isalpha() else 1
    return 0


def exact_candidates(
    source: SourceFormatting,
    sequence: str,
    surface_index: int,
    ordinal: int,
    text: str,
) -> tuple[EntryCandidate, ...]:
    """Every occurrence of the wording in source order, never capped."""
    wanted = _folded(text)
    if not wanted:
        return ()
    result: list[EntryCandidate] = []
    at = source.normalized.find(wanted)
    while at >= 0:
        start = source.positions[at]
        end = source.positions[at + len(wanted) - 1] + 1
        if text[0].isspace():
            while start > 0 and source.text[start - 1].isspace():
                start -= 1
        if text[-1].isspace():
            while end < len(source.text) and source.text[end].isspace():
                end += 1
        unit_start, unit_end = entry_unit_bounds(source, start)
        label_start = entry_label_start(source, unit_start, start, ordinal)
        result.append(
            EntryCandidate(
                surface_index=surface_index,
                ordinal=ordinal,
                start=start,
                end=end,
                unit_start=unit_start,
                unit_end=unit_end,
                label_start=label_start,
                preference=_label_preference(sequence, source, label_start),
            )
        )
        at = source.normalized.find(wanted, at + 1)
    return tuple(result)


@dataclass(frozen=True)
class _Score:
    """Assigned entries, then labelled occurrences, then preferred label families."""

    assigned: int
    labelled: int
    preferred: int
    evidence: int = 0

    def plus(self, candidate: EntryCandidate) -> "_Score":
        return _Score(
            assigned=self.assigned + 1,
            labelled=self.labelled + (1 if candidate.label_start is not None else 0),
            preferred=self.preferred - candidate.preference,
            evidence=self.evidence + candidate.evidence,
        )

    def better_than(self, other: "_Score") -> bool:
        return (self.assigned, self.labelled, self.evidence, self.preferred) > (
            other.assigned,
            other.labelled,
            other.evidence,
            other.preferred,
        )


def _blocked(candidate: EntryCandidate, blocked: tuple[tuple[int, int], ...]) -> bool:
    return any(candidate.start < end and start < candidate.end for start, end in blocked)


def assign_candidates(
    entry_counts: tuple[int, ...],
    candidates: list[EntryCandidate],
    *,
    blocked: tuple[tuple[int, int], ...] = (),
) -> dict[tuple[int, int], EntryCandidate]:
    """Allocate ordered disjoint slots, using an optimum fast path or dominance DP.

    Scores prefer assignment count, printed labels, wording evidence and then
    label-family conventions. Body/carrier-owned spans are excluded first.
    The ambiguous path advances a surface ordinal or skips it; equivalent
    later occurrences never need separate transitions or stored result paths.
    """
    if not candidates:
        return {}
    by_entry: dict[tuple[int, int], list[EntryCandidate]] = {}
    for candidate in candidates:
        if not _blocked(candidate, blocked):
            by_entry.setdefault((candidate.surface_index, candidate.ordinal), []).append(candidate)
    # If every entry's individually best slot is unique and the slots are
    # disjoint and ordered, their union is already the global optimum. Printed
    # labels make this the ordinary path, including arbitrarily many duplicates.
    anchored: list[EntryCandidate] = []
    for index, count in enumerate(entry_counts):
        for ordinal in range(1, count + 1):
            options = by_entry.get((index, ordinal), [])
            if not options:
                continue
            rank = max((c.label_start is not None, c.evidence, -c.preference) for c in options)
            best = [
                c for c in options if (c.label_start is not None, c.evidence, -c.preference) == rank
            ]
            if len(best) == 1:
                anchored.append(best[0])
    ordered = sorted(anchored, key=lambda c: (c.start, c.surface_index, c.ordinal))
    last_ordinal: dict[int, int] = {}
    disjoint = True
    end = 0
    for candidate in ordered:
        if candidate.start < end or candidate.ordinal <= last_ordinal.get(
            candidate.surface_index, 0
        ):
            disjoint = False
            break
        end = candidate.end
        last_ordinal[candidate.surface_index] = candidate.ordinal
    if len(anchored) == sum(entry_counts) and disjoint:
        return {(c.surface_index, c.ordinal): c for c in anchored}
    surfaces = len(entry_counts)
    memo: dict[tuple[tuple[int, ...], int], tuple[_Score, tuple[EntryCandidate, ...]]] = {}

    def solve(ordinals: tuple[int, ...], source_end: int):
        if all(ordinals[index] > entry_counts[index] for index in range(surfaces)):
            return _Score(0, 0, 0), ()
        key = (ordinals, source_end)
        if key in memo:
            return memo[key]
        best_score: _Score | None = None
        best_path: tuple[EntryCandidate, ...] = ()
        transitions: list[tuple[int, EntryCandidate]] = []
        for index in range(surfaces):
            ordinal = ordinals[index]
            if ordinal > entry_counts[index]:
                continue
            # At equal evidence/preference the earliest ending occurrence
            # dominates every later one: it leaves every suffix available.
            # Keep one transition per score class, not every occurrence.
            earliest: dict[tuple[int, int, bool], EntryCandidate] = {}
            for candidate in by_entry.get((index, ordinal), ()):
                if candidate.start < source_end:
                    continue
                rank = (candidate.preference, candidate.evidence, candidate.label_start is not None)
                prior = earliest.get(rank)
                if prior is None or (candidate.end, candidate.start) < (prior.end, prior.start):
                    earliest[rank] = candidate
            transitions.extend((index, candidate) for candidate in earliest.values())
        transitions.sort(key=lambda item: (item[1].start, item[0], item[1].ordinal))
        for index, candidate in transitions:
            next_ordinals = ordinals[:index] + (ordinals[index] + 1,) + ordinals[index + 1 :]
            sub_score, sub_path = solve(next_ordinals, candidate.end)
            score = sub_score.plus(candidate)
            if best_score is None or score.better_than(best_score):
                best_score, best_path = score, (candidate, *sub_path)
        for index in range(surfaces):
            if ordinals[index] > entry_counts[index]:
                continue
            next_ordinals = ordinals[:index] + (ordinals[index] + 1,) + ordinals[index + 1 :]
            sub_score, sub_path = solve(next_ordinals, source_end)
            if best_score is None or sub_score.better_than(best_score):
                best_score, best_path = sub_score, sub_path
        memo[key] = (best_score if best_score is not None else _Score(0, 0, 0), best_path)
        return memo[key]

    _score, path = solve(tuple(1 for _ in range(surfaces)), 0)
    return {(candidate.surface_index, candidate.ordinal): candidate for candidate in path}
