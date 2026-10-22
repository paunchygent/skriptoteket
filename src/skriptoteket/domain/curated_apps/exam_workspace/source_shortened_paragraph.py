"""A shortened own paragraph rebuilds its whole source extent (TASK-SKRIPT-REP-0049 review F2).

After the coverage gate, a text-only body paragraph that the exact path projected from
its own source keeps only its rendered extent: the restore's unit is the output's whole
source extent, from its origin to the largest source end projected into that origin, so
a joined row rebuilds every cell it rendered. A reply that split one source paragraph
into consecutive outputs restores as one group. Reworded (aligned-path) paragraphs keep
the model's wording, and nothing is flagged. A remainder that a choice shows stays out,
as does a remainder that is only a blank run, an inline answer label, or text a choice
shows. Source-offset sets and the projection's recorded extents decide; the reply body
wording is never compared, and no fuzzy matching is used.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    BLANK_RUN,
    QUESTION_HEADING_LABEL,
)
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
    visible_intervals,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_misplaced_paragraph import (
    own_source_span,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_paragraph_match import (
    SourceParagraph,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
        SourceFormatting,
    )


def _restore_start(body_source: SourceFormatting, paragraph: SourceParagraph) -> int:
    """Where the restore counts missing text from for one source paragraph.

    The question's own printed number is our list label's job, never restored
    (merged pre-push failure; Skriptoteket names questions by its own list labels,
    never by the source's numbering): when the paragraph opens the question
    (the first ``available_paragraphs`` entry with visible text) and
    ``QUESTION_HEADING_LABEL`` matches at its start, the match end is the start.
    """
    start = body_source.content_start(paragraph)
    if start != paragraph.start:
        return start
    first_visible: SourceParagraph | None = None
    for candidate in body_source.available_paragraphs:
        if any(
            segment.text.strip()
            for segment in body_source.visible_text_segments(candidate.start, candidate.end)
        ):
            first_visible = candidate
            break
    if first_visible is None or paragraph.start != first_visible.start:
        return start
    match = QUESTION_HEADING_LABEL.match(body_source.text, paragraph.start, paragraph.end)
    if match is None:
        return start
    return match.end()


def _paragraph_has_missing(
    text: str,
    paragraph: SourceParagraph,
    content_start: int,
    excluded: tuple[tuple[int, int], ...],
    accounted: set[int],
) -> bool:
    """Whether the source paragraph holds visible text no surface shows."""
    blank = {
        index
        for match in BLANK_RUN.finditer(text[paragraph.start : paragraph.end])
        for index in range(paragraph.start + match.start(), paragraph.start + match.end())
    }
    return any(
        not text[index].isspace() and index not in blank and index not in accounted
        for left, right in visible_intervals(content_start, paragraph.end, excluded)
        for index in range(left, right)
    )


def restore_shortened_paragraphs(
    chunks: tuple[DocxChunk, ...],
    sources: Iterable[SourceFormatting],
    body_source: SourceFormatting,
    body: tuple[NativeParagraph, ...],
    *,
    entries: Iterable[NativeSourceEntry],
) -> tuple[NativeParagraph, ...]:
    """Replace each shortened exact-path output by its whole source extent.

    An output is a candidate when its anchor is in ``exact_origins``. Its source extent
    is ``[anchor, exact_extents[anchor])``; its source paragraphs are the body-source
    paragraphs overlapping that extent. Consecutive outputs whose paragraph sets share
    a paragraph form one group (a reply that split one source paragraph). A group with
    an ``other_origins`` value in its paragraphs, an inline answer label, or a picture
    is skipped. A group is restored when any of its paragraphs holds a missing
    character, and is replaced by one paragraph built over the whole span. A group
    whose missing characters lie in a facit_shared span is restored too, so
    ``own_source_span`` raises and the item goes to review instead of showing
    text the facit repeats (rereview F4, decision A).
    """
    accounted = accounted_characters(chunks, sources, body_source, entries)
    text = body_source.text
    merged = list(zip(body_source.output_anchors, body, strict=True))
    extents = body_source.exact_extents
    candidate_paras: dict[int, tuple[SourceParagraph, ...]] = {}
    for index, (anchor, _) in enumerate(merged):
        if anchor not in body_source.exact_origins or anchor not in extents:
            continue
        end = extents[anchor]
        if end <= anchor:
            continue
        paras = tuple(
            paragraph
            for paragraph in body_source.paragraphs
            if paragraph.start < end and paragraph.end > anchor
        )
        if paras:
            candidate_paras[index] = paras
    groups: list[list[int]] = []
    for index in sorted(candidate_paras):
        current = {paragraph.start for paragraph in candidate_paras[index]}
        if groups and groups[-1][-1] == index - 1:
            previous = {paragraph.start for paragraph in candidate_paras[groups[-1][-1]]}
            if current & previous:
                groups[-1].append(index)
                continue
        groups.append([index])
    start_to_group = {group[0]: group for group in groups}
    rebuilt = False
    result: list[tuple[int, NativeParagraph]] = []
    cursor = 0
    while cursor < len(merged):
        group = start_to_group.get(cursor)
        if group is None:
            result.append(merged[cursor])
            cursor += 1
            continue
        union = sorted(
            {paragraph for index in group for paragraph in candidate_paras[index]},
            key=lambda paragraph: paragraph.start,
        )
        first, last = union[0], union[-1]
        skip = any(
            any(paragraph.start <= origin < paragraph.end for paragraph in union)
            for origin in body_source.other_origins
        )
        if not skip and ANSWER_LABEL.search(text, body_source.content_start(first), last.end):
            skip = True
        if not skip and body_source.provenance.pictures_in(first.start, last.end):
            skip = True
        if not skip and not any(
            _paragraph_has_missing(
                text,
                paragraph,
                _restore_start(body_source, paragraph),
                body_source.excluded,
                accounted,
            )
            for paragraph in union
        ):
            skip = True
        if skip:
            result.extend(merged[index] for index in group)
            cursor = group[-1] + 1
            continue
        built = own_source_span(body_source, first, last, start=_restore_start(body_source, first))
        if built is None:
            result.extend(merged[index] for index in group)
            cursor = group[-1] + 1
            continue
        result.append((first.start, built))
        rebuilt = True
        cursor = group[-1] + 1
    if not rebuilt:
        return body
    body = tuple(value for _, value in result)
    body_source.output_anchors = [anchor for anchor, _ in result]
    body_source.path = "rebuilt"
    return body
