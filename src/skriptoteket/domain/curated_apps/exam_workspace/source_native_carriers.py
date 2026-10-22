"""Classify only recovered source spans; produced visible text has authority."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    SCORE_FIELD,
    points_only_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_carrier_context import quoted_mask
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import source_tokens
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import ANSWER_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    normalized_source_index,
)

_ITALIC_TAG = re.compile(r"</?i>")
_FACIT_SENTENCE_SPLIT = re.compile(r"\r?\n|(?<=[.?!;])\s+")


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


def _facit_sentences(facit: str) -> list[str]:
    """The facit's sentences after its italic tags are stripped, like the reply contract."""
    cleaned = _ITALIC_TAG.sub("", facit)
    return [part.strip() for part in _FACIT_SENTENCE_SPLIT.split(cleaned) if part.strip()]


def _wholly_unemitted(text: str, start: int, end: int, emitted: frozenset[int]) -> bool:
    """Whether the reply emitted none of the span: a facit run the reply partly emitted
    still shows its question through the reply's own projection (a gap carries the answer),
    so only a wholly unemitted run is key-owned."""
    return all(
        position not in emitted for position in range(start, end) if not text[position].isspace()
    )


def _occurrence_in_regions(
    normalized: str,
    positions: list[int],
    needle: str,
    text: str,
    search: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    """First needle occurrence wholly inside one search region, on word boundaries."""
    start = 0
    while True:
        found = normalized.find(needle, start)
        if found < 0:
            return None
        source_start = positions[found]
        source_end = positions[found + len(needle) - 1] + 1
        if (
            any(left <= source_start and source_end <= right for left, right in search)
            and (source_start == 0 or text[source_start - 1].isspace())
            and (source_end == len(text) or text[source_end].isspace())
        ):
            return source_start, source_end
        start = found + 1


def _facit_carrier_spans(
    text: str,
    *,
    normalized: str,
    positions: list[int],
    sentences: list[str],
    search: tuple[tuple[int, int], ...],
    emitted: frozenset[int],
) -> list[tuple[int, int]]:
    """Longest facit sentence runs the reply did not emit, as source spans."""
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(sentences):
        matched: tuple[int, tuple[int, int]] | None = None
        for stop in range(len(sentences) - 1, index - 1, -1):
            needle, _ = normalized_source_index(" ".join(sentences[index : stop + 1]))
            if not needle:
                continue
            found = _occurrence_in_regions(normalized, positions, needle, text, search)
            if found is not None:
                matched = (stop, found)
                break
        if matched is None:
            index += 1
            continue
        stop, (start, end) = matched
        if _wholly_unemitted(text, start, end, emitted):
            spans.append((start, end))
        index = stop + 1
    return spans


def native_carrier_spans(
    text: str,
    *,
    points: int | float | None = None,
    emitted: frozenset[int] = frozenset(),
    regions: tuple[tuple[int, int], ...] = (),
    body_regions: tuple[tuple[int, int], ...] = (),
    facit: str | None = None,
) -> tuple[tuple[int, int], ...]:
    """Classify omitted metadata inside complete source owners.

    A recovered answer label owns the rest of its region, including subsequent
    lines and paragraphs. A recovered score belongs to the native points field
    only when its numeric value agrees. A recovered score whose line holds only
    a score field, such as "/4 p", or only a points line holding one label, such
    as "Poäng: 6 poäng", excludes the whole line. Complete emitted labels and scores
    stay visible; a recovered carrier is excluded atomically so coincidental
    provenance cannot leak its value into a source reconstruction. Projection
    retains authority over the model's visible wording. Answer values are
    never recovered into a native facit field.

    Source text the item's facit copies verbatim, and that the reply did not emit,
    is a recovered key carrier too (TASK-SKRIPT-REP-0049 review F3/F1): the reply
    contract keeps the teacher's facit wording verbatim while text segments never
    carry inline facit, so such text is key-owned. Each longest run of consecutive
    facit sentences found whitespace-folded in one owner or body region, on word
    boundaries and with none of its wording emitted by the reply, becomes one span:
    a run the reply partly emitted still shows its question through the reply's own
    projection (a gap carries the answer), so gap_fill facits that restate the
    question change nothing. Exact substring search over the normalized index only;
    no fuzzy match, no token overlap, no wording list.
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
            line_end = text.find("\n", match.start())
            if line_end < 0:
                line_end = len(text)
            # A score field widens only within the line that holds the match start.
            # A points-only line holding exactly one label leaves whole the same way.
            line = text[line_start:line_end]
            if match.end() <= line_end and (
                SCORE_FIELD.fullmatch(text, line_start, line_end) or points_only_line(line)
            ):
                spans.append((line_start, line_end))
            else:
                spans.append((match.start(), match.end()))
    # Labels and scores are atomic metadata units. A recovered label owns
    # its answer tail even if a word elsewhere in the model happens to match.
    if facit:
        normalized, positions = normalized_source_index(text)
        spans.extend(
            _facit_carrier_spans(
                text,
                normalized=normalized,
                positions=positions,
                sentences=_facit_sentences(facit),
                search=(*regions, *body_regions),
                emitted=emitted,
            )
        )
    return tuple(sorted(spans))
