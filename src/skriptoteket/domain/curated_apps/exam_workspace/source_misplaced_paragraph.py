"""Another question's source is never this item's content (TASK-SKRIPT-39-04-15 D4/D5).

A text-only reply paragraph whose whole text is one other chunk's source span is
rebuilt from this item's own source paragraph with every excluded interval inside
it removed. Task 16's shared source_paragraph() builder replaces _source_paragraph
when this branch merges after it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import (
    normalized_source_index,
    visible_intervals,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
        SourceFormatting,
    )


def _trim_edge_whitespace(
    segments: tuple[NativeTextSegment, ...],
) -> tuple[NativeTextSegment, ...]:
    """Drop a rebuilt paragraph's outer whitespace without touching any mark.

    An excluded span such as a points label can leave a space at a rebuilt
    paragraph's boundary, so only the first and last text segment lose
    whitespace; an emptied segment disappears and interior spacing stays.
    """
    if not segments:
        return segments
    trimmed = list(segments)
    trimmed[0] = trimmed[0].model_copy(update={"text": trimmed[0].text.lstrip()})
    trimmed[-1] = trimmed[-1].model_copy(update={"text": trimmed[-1].text.rstrip()})
    return tuple(segment for segment in trimmed if segment.text)


def is_misplaced(source: SourceFormatting, paragraph: NativeParagraph) -> bool:
    """Whether a text-only reply paragraph is another question's source and so never this
    item's content (TASK-SKRIPT-39-04-15 D4): its whole text is one other chunk's source span,
    never a match straddling the boundary between two chunks. Ownership is a property of
    this item's whole own source, never of the rendering cursor: text occurring anywhere in
    this item's own normalized source is owned even when the cursor has consumed its span."""
    if any(segment.kind != "text" for segment in paragraph.segments):
        return False
    text = "".join(segment.text for segment in paragraph.segments if segment.kind == "text")
    wanted, _ = normalized_source_index(text)
    if not wanted:
        return False
    if wanted in source.normalized:
        return False
    return any(wanted in chunk for chunk in source.foreign_normalized)


def rebuild_misplaced(source: SourceFormatting) -> list[tuple[NativeParagraph, int]]:
    """Rebuild a misplaced paragraph from this item's next own source paragraph no output
    has shown, or return nothing to drop it; the entry span stays unaligned.

    The candidate is a whole source paragraph (TASK-SKRIPT-39-04-15 D4/D5): an
    excluded interval inside it is removed text, never a paragraph boundary.
    An own paragraph that cannot be rendered raises instead of being silently dropped."""
    start = (
        source.positions[source.cursor]
        if source.cursor < len(source.positions)
        else len(source.text)
    )
    paragraph = next(
        (
            p
            for p in source.paragraphs
            if p.start >= start
            # A paragraph is shown when any excluded-interval fragment of it was shown.
            and not any(
                fragment in source.projected
                for fragment in source.available_paragraphs
                if p.start <= fragment.start < p.end
            )
            and any(
                segment.text.strip()
                for segment in source.visible_text_segments(source.content_start(p), p.end)
            )
        ),
        None,
    )
    if paragraph is None:
        return []
    built = _source_paragraph(source, paragraph.start)
    if built is None:
        return []
    source.path = "rebuilt"
    while source.cursor < len(source.positions) and source.positions[source.cursor] < paragraph.end:
        source.cursor += 1
    return [(built, paragraph.start)]


def _source_paragraph(source: SourceFormatting, origin: int) -> NativeParagraph | None:
    """Build this item's own source paragraph, never another question's source: a
    paragraph whose text is another question's source is not this item's content (D4).

    The whole paragraph is rendered with every excluded interval inside it removed
    (D5); removing one must not leave two spaces at the join it creates.
    A paragraph with a source picture or an inline answer key cannot be rebuilt and
    raises; only a paragraph with no visible text returns None."""
    paragraph = next((p for p in source.paragraphs if p.start <= origin < p.end), None)
    if paragraph is None:
        return None
    start = source.content_start(paragraph)
    if ANSWER_LABEL.search(source.text[start : paragraph.end]):
        raise FormattingTransferError(
            "misplaced paragraph's own source cannot be rebuilt: inline answer key"
        )
    if source.provenance.has_picture_in(paragraph.start, paragraph.end):
        raise FormattingTransferError("misplaced paragraph's own source cannot be rebuilt: picture")
    joined: list[NativeTextSegment] = []
    for segment in source.visible_text_segments(start, paragraph.end):
        if joined and joined[-1].text[-1:].isspace() and segment.text[:1].isspace():
            joined[-1] = joined[-1].model_copy(update={"text": joined[-1].text.rstrip()})
        joined.append(segment)
    segments = _trim_edge_whitespace(tuple(joined))
    if not any(segment.text.strip() for segment in segments):
        return None
    for left, right in visible_intervals(start, paragraph.end, source.excluded):
        source.covered.update(range(left, right))
    source.projected.update(
        fragment.start
        for fragment in source.available_paragraphs
        if paragraph.start <= fragment.start < paragraph.end
    )
    return NativeParagraph(heading_level=paragraph.heading, segments=segments)
