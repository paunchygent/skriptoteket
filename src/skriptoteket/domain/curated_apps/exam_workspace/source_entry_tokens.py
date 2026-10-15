"""Whole-token alignment candidates for the joint native-entry allocator.

Every source interval remains available. Edit scores reward copied tokens and
charge substitutions, omissions and insertions; unlike character alignment a
shared article cannot move an ownership edge into another word. The caller
assigns these intervals jointly with exact anchors before projecting any entry.
"""

from __future__ import annotations

import re

from skriptoteket.domain.curated_apps.exam_workspace.source_entry_alignment import (
    EntryCandidate,
    entry_unit_bounds,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def token_candidates(
    source: SourceFormatting,
    surface_index: int,
    ordinal: int,
    wording: str,
    blocked: tuple[tuple[int, int], ...],
) -> list[EntryCandidate]:
    """Score all nonempty token intervals by ordered edit alignment.

    Running a row per possible source start preserves alternatives that a
    per-entry best-paragraph or local alignment would discard. A source barrier
    splits the edit graph, so no candidate can absorb body or labelled owners.
    Exact-copy allocation bypasses this graph entirely.
    """
    wanted = [m.group().casefold() for m in _TOKEN.finditer(wording)]
    if not wanted:
        return []
    tokens = list(_TOKEN.finditer(source.text))
    available = [
        not any(m.start() < end and start < m.end() for start, end in blocked) for m in tokens
    ]
    result: list[EntryCandidate] = []
    for begin, first in enumerate(tokens):
        if not available[begin]:
            continue
        previous = [-2 * i for i in range(len(wanted) + 1)]
        for finish in range(begin, len(tokens)):
            if not available[finish]:
                break
            token = tokens[finish]
            value = token.group().casefold()
            current = [-(finish - begin + 1)]
            for index, expected in enumerate(wanted, start=1):
                current.append(
                    max(
                        previous[index - 1] + (3 if expected == value else -2),
                        previous[index] - 1,
                        current[index - 1] - 2,
                    )
                )
            previous = current
            unit_start, unit_end = entry_unit_bounds(source, first.start())
            result.append(
                EntryCandidate(
                    surface_index=surface_index,
                    ordinal=ordinal,
                    start=first.start(),
                    end=token.end(),
                    unit_start=unit_start,
                    unit_end=unit_end,
                    label_start=None,
                    preference=2,
                    evidence=current[-1],
                )
            )
    return result


def exact_token_score(wording: str) -> int:
    """The edit graph's upper bound for a fully copied entry."""
    return 3 * len(_TOKEN.findall(wording))
