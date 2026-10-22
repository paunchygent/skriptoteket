"""A shortened own paragraph shows its whole own source paragraph (TASK-SKRIPT-REP-0049).

After the coverage gate, a text-only body paragraph that the exact path projected from
its own source paragraph, and whose own source paragraph holds visible text that no
surface of the item shows, is replaced by its whole own source paragraph. Reworded
(aligned-path) paragraphs keep the model's wording, and nothing is flagged. A remainder
the item's facit shows stays out, as does a remainder that is only a blank run, an
inline answer label's paragraph, or text a choice shows.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import BLANK_RUN
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    accounted_characters,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    normalized_source_index,
    visible_intervals,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_misplaced_paragraph import (
    own_source_paragraph,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
        SourceFormatting,
    )


def _missing_stretches(
    text: str,
    start: int,
    end: int,
    excluded: tuple[tuple[int, int], ...],
    missing: set[int],
) -> list[tuple[int, int]]:
    """Maximal missing runs separated only by whitespace, as source spans.

    A non-whitespace accounted character ends a stretch; an excluded interval does too,
    so a stretch never spans removed source text.
    """
    stretches: list[tuple[int, int]] = []
    current: list[int] = []
    for left, right in visible_intervals(start, end, excluded):
        for index in range(left, right):
            if index in missing:
                current.append(index)
            elif not text[index].isspace() and current:
                stretches.append((current[0], current[-1] + 1))
                current = []
        if current:
            stretches.append((current[0], current[-1] + 1))
            current = []
    return stretches


def restore_shortened_paragraphs(
    chunks: tuple[DocxChunk, ...],
    sources: Iterable[SourceFormatting],
    body_source: SourceFormatting,
    body: tuple[NativeParagraph, ...],
    *,
    entries: Iterable[NativeSourceEntry],
    facit_text: str | None,
) -> tuple[NativeParagraph, ...]:
    """Replace each shortened exact-path body paragraph by its whole own source paragraph.

    A source paragraph is a candidate only when an exact-path origin lies inside it and
    no other-path origin does. Decisions read source alignment, source classification
    and the facit surface only; the reply body wording is never compared, and no fuzzy
    matching is used.
    """
    accounted = accounted_characters(chunks, sources, body_source, entries)
    facit, _ = normalized_source_index(facit_text) if facit_text else ("", [])
    text = body_source.text
    for paragraph in body_source.paragraphs:
        if not any(
            paragraph.start <= origin < paragraph.end for origin in body_source.exact_origins
        ):
            continue
        if any(paragraph.start <= origin < paragraph.end for origin in body_source.other_origins):
            continue
        start = body_source.content_start(paragraph)
        if ANSWER_LABEL.search(text, start, paragraph.end):
            continue
        if body_source.provenance.pictures_in(paragraph.start, paragraph.end):
            continue
        blank = {
            index
            for match in BLANK_RUN.finditer(text[paragraph.start : paragraph.end])
            for index in range(paragraph.start + match.start(), paragraph.start + match.end())
        }
        missing = {
            index
            for left, right in visible_intervals(start, paragraph.end, body_source.excluded)
            for index in range(left, right)
            if not text[index].isspace() and index not in blank and index not in accounted
        }
        if not missing:
            continue
        stretches = [
            (left, right)
            for left, right in _missing_stretches(
                text, start, paragraph.end, body_source.excluded, missing
            )
            # The facit surface shows this remainder, so the body must not.
            if normalized_source_index(text[left:right])[0] not in facit
        ]
        if not stretches:
            continue
        merged = list(zip(body_source.output_anchors, body, strict=True))
        positions = [
            index
            for index, (anchor, _) in enumerate(merged)
            if paragraph.start <= anchor < paragraph.end
        ]
        if not positions:
            continue
        built = own_source_paragraph(body_source, paragraph.start)
        if built is None:
            continue
        kept = [entry for index, entry in enumerate(merged) if index not in positions[1:]]
        kept[positions[0]] = (paragraph.start, built)
        body = tuple(value for _, value in kept)
        body_source.output_anchors = [anchor for anchor, _ in kept]
        body_source.path = "rebuilt"
    return body
