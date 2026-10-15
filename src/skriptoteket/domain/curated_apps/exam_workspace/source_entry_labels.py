"""Index printed entry slots before matching any produced wording.

Labels identify source owners independently of model rewrites. All surfaces
share the same slot edges; wording evidence can score a slot, never move its
edge into another entry's words. Numeric/alphabetic side conventions are soft
preferences: actual wording evidence outranks them.
"""

from __future__ import annotations

import re
from bisect import bisect_left

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_alignment import (
    EntryCandidate,
    _label_preference,
    assign_candidates,
    entry_unit_bounds,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    _ORDINAL_FAMILIES,
    _ordinal_token,
    entry_label_end,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

_TOKEN = re.compile(r"(?<!\S)[([{]?(?P<token>[A-Za-z0-9]+)[)\]}.:;\-–—]+\s*")


def labelled_slots(
    source: SourceFormatting,
    sequences: tuple[str, ...],
    texts: tuple[tuple[str, ...], ...],
    blocked: tuple[tuple[int, int], ...],
) -> dict[tuple[int, int], tuple[EntryCandidate, tuple[int, int] | None]]:
    """Assign disjoint labelled slots jointly, including wholly rewritten entries.

    The index visits token boundaries once. Each recognised ordinal shares one
    source slot with every surface; the ordered assignment resolves family and
    duplicate-label ambiguity. Common repeated wording is looked up only inside
    its slot, never expanded into the entry-by-occurrence cross product.
    """
    ordinals: dict[str, set[int]] = {}
    for ordinal in range(1, max(map(len, texts), default=0) + 1):
        for family in _ORDINAL_FAMILIES:
            token_text = _ordinal_token(family, ordinal)
            if token_text is not None:
                ordinals.setdefault(token_text, set()).add(ordinal)
    labels: dict[int, list[tuple[int, int]]] = {}
    families: dict[tuple[int, int], tuple[str, ...]] = {}
    family_ordinals: dict[str, set[int]] = {}
    for token in _TOKEN.finditer(source.text):
        start = token.start()
        if any(a <= start < b for a, b in blocked):
            continue
        for ordinal in sorted(ordinals.get(token.group("token"), ())):
            size = entry_label_end(token.group(), ordinal)
            if size is not None:
                labels.setdefault(start, []).append((ordinal, size))
                matches = tuple(
                    family
                    for family in _ORDINAL_FAMILIES
                    if _ordinal_token(family, ordinal) == token.group("token")
                )
                families[start, ordinal] = matches
                for family in matches:
                    family_ordinals.setdefault(family, set()).add(ordinal)
    starts = sorted(labels)
    support = {family: len(values) for family, values in family_ordinals.items()}
    maximum = max(support.values(), default=0)
    candidates: list[EntryCandidate] = []
    anchors: dict[tuple[int, int, int], tuple[int, int] | None] = {}
    folded = {
        text: SourceFormatting((DocxChunk("fold", "paragraph", text, text),)).normalized
        for surface in texts
        for text in surface
    }
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(source.text)
        # A body or carrier between entries stops the visible slot as well.
        end = min((a for a, _ in blocked if start < a < end), default=end)
        unit_start, unit_end = entry_unit_bounds(source, start)
        for ordinal, size in labels[start]:
            for index, (sequence, surface) in enumerate(zip(sequences, texts, strict=True)):
                if ordinal > len(surface):
                    continue
                wanted = folded[surface[ordinal - 1]]
                lo = bisect_left(source.positions, start + size)
                hi = bisect_left(source.positions, end)
                at = source.normalized.find(wanted, lo, hi) if wanted else -1
                anchor = (
                    None
                    if at < 0
                    else (
                        source.positions[at],
                        source.positions[at + len(wanted) - 1] + 1,
                    )
                )
                candidate = EntryCandidate(
                    surface_index=index,
                    ordinal=ordinal,
                    start=start,
                    end=end,
                    unit_start=unit_start,
                    unit_end=unit_end,
                    label_start=start,
                    preference=(
                        _label_preference(sequence, source, start) * (maximum + 1)
                        + maximum
                        - max(support[f] for f in families[start, ordinal])
                    ),
                    evidence=int(anchor is not None),
                )
                candidates.append(candidate)
                anchors[index, ordinal, start] = anchor
    assigned = assign_candidates(tuple(map(len, texts)), candidates)
    return {key: (candidate, anchors[*key, candidate.start]) for key, candidate in assigned.items()}
