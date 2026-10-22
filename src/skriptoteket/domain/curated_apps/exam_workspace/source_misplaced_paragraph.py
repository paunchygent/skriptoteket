"""Another question's source is never this item's content (TASK-SKRIPT-39-04-15 D4/D5).

A text-only reply paragraph whose whole text is one other chunk's source span is
rebuilt from this item's own source paragraph with every excluded interval inside
it removed, through TASK-SKRIPT-39-04-16's shared source_paragraph() builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
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
from skriptoteket.domain.curated_apps.exam_workspace.source_gap_paragraphs import (
    source_paragraph,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
        SourceFormatting,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.source_paragraph_match import (
        SourceParagraph,
    )


def is_misplaced(source: SourceFormatting, paragraph: NativeParagraph) -> bool:
    """Whether a text-only reply paragraph is another question's source and so never this
    item's content (TASK-SKRIPT-39-04-15 D4): its whole text is one other chunk's source span,
    never a match straddling the boundary between two chunks. Ownership is a property of
    this item's whole own source, never of the rendering cursor: text occurring anywhere in
    this item's own normalized source is owned even when the cursor has consumed its span."""
    return _repeats(source, paragraph, source.foreign_normalized)


def is_released(source: SourceFormatting, paragraph: NativeParagraph) -> bool:
    """Whether a text-only reply paragraph is a part line admission moved out of the reply's
    entries (review F1, user ruling 2026-10-18 DEL 4): its whole text is one released line's
    source span, whole or a fragment, and no text of this item's own source. Such a paragraph
    is the part's source, which its parent shows, so it leaves the body without a rebuild."""
    return _repeats(source, paragraph, source.released_normalized)


def holds_released(source: SourceFormatting, paragraph: NativeParagraph) -> bool:
    """Whether a reply paragraph holds released part-line source beside other text, where this
    item's own source holds no such text: the part's source shares the paragraph with the
    question's, and no source alignment separates them (review F1). The released source is a
    whole released line anywhere in the paragraph, or a fragment of one that opens or closes
    the paragraph at a word boundary."""
    text = "".join(segment.text for segment in paragraph.segments if segment.kind == "text")
    wanted, _ = normalized_source_index(text)
    lines = tuple(line for line in source.released_normalized if line)
    if any(line in wanted and line not in source.normalized for line in lines):
        return True
    words = wanted.split(" ")
    edges = (
        edge
        for cut in range(1, len(words))
        for edge in (" ".join(words[:cut]), " ".join(words[cut:]))
    )
    return any(
        edge not in source.normalized and any(edge in line for line in lines) for edge in edges
    )


def _repeats(source: SourceFormatting, paragraph: NativeParagraph, others: tuple[str, ...]) -> bool:
    """Whether the paragraph's whole text lies inside one of ``others`` and nowhere in this
    item's own normalized source."""
    if any(segment.kind != "text" for segment in paragraph.segments):
        return False
    text = "".join(segment.text for segment in paragraph.segments if segment.kind == "text")
    wanted, _ = normalized_source_index(text)
    if not wanted:
        return False
    if wanted in source.normalized:
        return False
    return any(wanted in chunk for chunk in others)


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
                fragment.start in source.projected
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
    built = own_source_paragraph(source, paragraph.start)
    if built is None:
        return []
    source.path = "rebuilt"
    while source.cursor < len(source.positions) and source.positions[source.cursor] < paragraph.end:
        source.cursor += 1
    return [(built, paragraph.start)]


def own_source_span(
    source: SourceFormatting,
    first: SourceParagraph,
    last: SourceParagraph,
    *,
    start: int | None = None,
) -> NativeParagraph | None:
    """Build one output's whole source extent, never another question's source.

    The span runs from ``start`` (default ``content_start(first)``) to ``last.end``
    through the shared source_paragraph() builder, so a joined row rebuilds every
    cell it rendered with the " | " separators and the D5 join rule
    (TASK-SKRIPT-REP-0049 review F2). A caller restoring a shortened paragraph
    passes the question opening's restore start, so the question's own printed
    number is never restored: naming a question is our list label's job
    (merged pre-push failure; Skriptoteket names questions by its own list labels,
    never by the source's numbering). A span with a source picture or an inline
    answer key cannot be rebuilt and raises; only a span with no visible text
    returns None. The whole span is marked covered and projected."""
    start = source.content_start(first) if start is None else start
    end = last.end
    if ANSWER_LABEL.search(source.text[start:end]):
        raise FormattingTransferError(
            "misplaced paragraph's own source cannot be rebuilt: inline answer key"
        )
    source.refuse_facit_shared(start, end)
    if source.provenance.pictures_in(first.start, last.end):
        raise FormattingTransferError("misplaced paragraph's own source cannot be rebuilt: picture")
    built = source_paragraph(source, start, end, first.heading)
    if not any(segment.text.strip() for segment in built.segments if segment.kind == "text"):
        return None
    for left, right in visible_intervals(start, end, source.excluded):
        source.covered.update(range(left, right))
    source.projected.update(
        fragment.start
        for fragment in source.available_paragraphs
        if first.start <= fragment.start < last.end
    )
    return built


def own_source_paragraph(source: SourceFormatting, origin: int) -> NativeParagraph | None:
    """Build this item's own source paragraph, never another question's source: a
    paragraph whose text is another question's source is not this item's content (D4).

    The whole paragraph is rendered through the shared source_paragraph() builder with
    every excluded interval inside it removed (D5). A paragraph with a source picture
    or an inline answer key cannot be rebuilt and raises; only a paragraph with no
    visible text returns None."""
    paragraph = next((p for p in source.paragraphs if p.start <= origin < p.end), None)
    if paragraph is None:
        return None
    return own_source_span(source, paragraph, paragraph)
