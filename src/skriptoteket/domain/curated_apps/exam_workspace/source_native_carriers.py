"""Classify only recovered source spans; produced visible text has authority."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_carrier_context import quoted_mask
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import ANSWER_LABEL


def emitted_positions(source: str, emitted: str, offset: int = 0) -> frozenset[int]:
    """Source provenance of copied model text, without interpreting its content.

    Character alignment accounts for copied source words even when the model
    inserts letters or punctuation inside a word. A whole source word must be
    represented: isolated coincidental letters inside an omitted answer are not
    evidence that the model emitted that answer. No carrier grammar participates
    in this alignment.
    """
    matcher = SequenceMatcher(None, source, emitted, autojunk=False)
    represented = {
        position
        for block in matcher.get_matching_blocks()
        for position in range(block.a, block.a + block.size)
    }
    for word in re.finditer(r"\w+", source):
        positions = range(word.start(), word.end())
        if not all(position in represented for position in positions):
            represented.difference_update(positions)
    return frozenset(offset + position for position in represented)


def _recovered(text: str, start: int, end: int, emitted: frozenset[int]) -> bool:
    """A label is recovered only if the model did not emit its complete wording."""
    return not all(
        position in emitted for position in range(start, end) if not text[position].isspace()
    )


def native_carrier_spans(
    text: str,
    *,
    points: int | float | None = None,
    emitted: frozenset[int] = frozenset(),
    regions: tuple[tuple[int, int], ...] = (),
    body_regions: tuple[tuple[int, int], ...] = (),
) -> tuple[tuple[int, int], ...]:
    """Classify omitted metadata inside complete source owners.

    A recovered answer label owns the rest of its region, including subsequent
    lines and paragraphs. A recovered score belongs to the native points field
    only when its numeric value agrees. Emitted text is subtracted from every
    exclusion, so neither grammar can remove any model-emitted character.
    Answer values are never recovered into a native facit field.
    """
    mask = quoted_mask(text)
    spans: list[tuple[int, int]] = []
    for start, end in regions:
        for label in ANSWER_LABEL.finditer(text, start, end):
            if mask[label.start()] or not _recovered(text, label.start(), label.end(), emitted):
                continue
            left = label.start()
            # A wrapper around recovered metadata is recovered too.
            opening = text.rfind("(", start, left)
            if opening >= start and not text[opening + 1 : left].strip():
                left = opening
            spans.append((left, end))
            break
    for start, end in (*regions, *body_regions):
        if points is None:
            continue
        # A score is a complete recovered unit, not a substring of recovered
        # mathematical or prose content. Split gaps only at source block/clause
        # boundaries; emitted provenance itself also delimits recovered units.
        boundaries = {start, end}
        boundaries.update(edge for span in spans for edge in span if start < edge < end)
        boundaries.update(p for p in range(start + 1, end) if (p in emitted) != (p - 1 in emitted))
        boundaries.update(
            m.end() for m in re.compile(r"[.!?;\n](?:\s|$)").finditer(text, start, end)
        )
        edges = sorted(boundaries)
        units = tuple(zip(edges, edges[1:]))
        for match in POINT_LABEL.finditer(text, start, end):
            unit = next(
                (
                    (left, right)
                    for left, right in units
                    if left <= match.start() and match.end() <= right
                ),
                None,
            )
            if unit is None:
                continue
            left, right = unit
            residual = text[left : match.start()] + text[match.end() : right]
            if residual.strip(" \t\r\n.!?;:"):
                continue
            value = re.search(r"\d+(?:[.,]\d+)?", match.group())
            if (
                value is None
                or float(value.group().replace(",", ".")) != points
                or mask[match.start()]
                or not _recovered(text, match.start(), match.end(), emitted)
            ):
                continue
            spans.append((match.start(), match.end()))
    # Subtract provenance rather than relying on the label's shape, position,
    # quotation or punctuation to protect the content the model emitted.
    recovered: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        left = start
        for position in range(start, end):
            if position in emitted:
                if left < position:
                    recovered.append((left, position))
                left = position + 1
        if left < end:
            recovered.append((left, end))
    return tuple(recovered)
