"""Classify only recovered source spans; produced visible text has authority."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    SCORE_FIELD,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_carrier_context import quoted_mask
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import source_tokens
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import ANSWER_LABEL


def emitted_positions(source: str, emitted: str, offset: int = 0) -> frozenset[int]:
    """Exact ordered token runs establish content provenance.

    Character-level mark placement remains the projection layer's job: a
    source word can mark a prefix of a model word without establishing that
    another omitted source token was emitted as content.
    """
    original = source_tokens(source)
    produced = source_tokens(emitted)
    matcher = SequenceMatcher(
        None,
        [source[t.start : t.end] for t in original],
        [emitted[t.start : t.end] for t in produced],
        autojunk=False,
    )
    represented: set[int] = set()
    for block in matcher.get_matching_blocks():
        for token in original[block.a : block.a + block.size]:
            represented.update(range(token.start, token.end))
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
    only when its numeric value agrees. A recovered score whose line holds only
    a score field, such as "/4 p", excludes the whole line. Complete emitted labels and scores
    stay visible; a recovered carrier is excluded atomically so coincidental
    provenance cannot leak its value into a source reconstruction. Projection
    retains authority over the model's visible wording. Answer values are
    never recovered into a native facit field.
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
            # The recovered label owns its entire answer, not just letters
            # absent from other model words. Model content is projected from
            # the model, never reconstructed from a recovered answer value.
            spans.append((left, end))
            break
    for start, end in (*regions, *body_regions):
        if points is None:
            continue
        # A recovered annotation that agrees with the native field is
        # metadata even when it shares a gap with visible continuation.
        for match in POINT_LABEL.finditer(text, start, end):
            value = re.search(r"\d+(?:[.,]\d+)?", match.group())
            if (
                value is None
                or float(value.group().replace(",", ".")) != points
                or mask[match.start()]
                or not _recovered(text, match.start(), match.end(), emitted)
            ):
                continue
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end < 0:
                line_end = len(text)
            if SCORE_FIELD.fullmatch(text, line_start, line_end):
                spans.append((line_start, line_end))
            else:
                spans.append((match.start(), match.end()))
    # Labels and scores are atomic metadata units. A recovered label owns
    # its answer tail even if a word elsewhere in the model happens to match.
    return tuple(sorted(spans))
