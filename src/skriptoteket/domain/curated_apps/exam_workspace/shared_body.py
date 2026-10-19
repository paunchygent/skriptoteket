"""The one native body representation, shared by item bodies and instruction bodies.

Purpose:
    Item bodies, parent instructions and document instructions all carry
    ``tuple[NativeParagraph, ...]``: text runs, gap references and picture references
    placed exactly where they stand. This module builds that body from DOCX source
    chunks, each picture at its exact place in the chunk's text, and reads a body back
    as text lines or asset ids, so no consumer writes its own segment loop.

Relationships:
    - Written by ``docx_ai_build`` (review items and document instructions) and
      ``docx_section_instructions`` (parent instructions and carried wording).
    - Read by every plain-text consumer through ``body_text_lines``/``body_plain_text``
      and by asset accounting and the QTI/PDF exporters through ``body_asset_ids``.
    - Imports only the body leaf, the DOCX chunk record and the review-state vocabulary
      (the item itself only for typing), so nothing here can cycle back into the
      document or parent models.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxMissingImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
        NativeExamItem,
    )

_GAP_MARKER = "[___]"


def _missing_picture_text(missing: DocxMissingImage) -> str:
    return f"[Bild saknas: {missing.reference} ({missing.media_type})]"


def is_printed_answer_line(segments: Sequence[NativeSegment]) -> bool:
    """A printed answer line is answer space, not question text (W10).

    True only for a paragraph of text segments whose whole wording is whitespace and
    underscores with at least one underscore. Any gap or asset segment keeps the paragraph.
    """
    texts = [segment.text for segment in segments if isinstance(segment, NativeTextSegment)]
    return len(texts) == len(segments) and is_answer_line_text("".join(texts))


ANSWER_LINE_ONLY_REASON = "Frågan innehöll bara skrivlinjer i källan – kontrollera mot källan."


def without_printed_answer_lines(
    body: Iterable[NativeParagraph],
) -> tuple[NativeParagraph, ...]:
    """Every paragraph of ``body`` that is not a printed answer line, in order (W10).

    The gate only removes whole paragraphs; a kept paragraph is never edited, merged or
    rewritten. A paragraph carrying a gap or a picture is never a printed answer line.
    """
    return tuple(paragraph for paragraph in body if not is_printed_answer_line(paragraph.segments))


def without_item_answer_lines(item: NativeExamItem) -> NativeExamItem:
    """The item without printed answer-line paragraphs, whichever path rebuilt its body.

    An item the gate empties goes to teacher review with ``ANSWER_LINE_ONLY_REASON``,
    appended once to its existing reasons; an item whose body was already empty, or that
    keeps every paragraph, is returned untouched. Gaps, pictures and the source anchor
    are never changed.
    """
    kept = without_printed_answer_lines(item.body)
    if len(kept) == len(item.body):
        return item
    if kept:
        return item.model_copy(update={"body": kept})
    reasons = tuple(dict.fromkeys((*item.review.reasons, ANSWER_LINE_ONLY_REASON)))
    review = item.review.model_copy(
        update={"state": NativeItemReviewState.REVIEW_REQUIRED, "reasons": reasons}
    )
    return item.model_copy(update={"body": kept, "review": review})


def source_paragraph(chunk: DocxChunk) -> NativeParagraph | None:
    """One source chunk as a native paragraph, each picture at its exact source place.

    A picture the chunker could not turn into a ``DocxImage`` has no payload, so its exact
    place holds a named text placeholder instead: the teacher sees which picture is missing
    and where, and a picture-only chunk still becomes a non-empty paragraph. A text-less
    chunk without pictures becomes nothing.
    """
    source = SourceFormatting((chunk,))
    placements: list[tuple[int, NativeSegment]] = [
        (image.offset, NativeAssetSegment(asset_id=image.asset_id)) for image in chunk.images
    ]
    placements.extend(
        (missing.offset, NativeTextSegment(text=_missing_picture_text(missing), marks=()))
        for missing in chunk.missing_images
    )
    if not placements:
        if not chunk.text:
            return None
        return NativeParagraph(
            heading_level=source.paragraphs[0].heading if source.paragraphs else None,
            segments=source.text_segments(0, len(chunk.text)),
        )
    placements.sort(key=lambda placement: placement[0])
    segments: list[NativeSegment] = []
    cursor = 0
    for offset, segment in placements:
        before = chunk.text[cursor:offset]
        if before:
            segments.extend(source.text_segments(cursor, offset))
        segments.append(segment)
        cursor = offset
    after = chunk.text[cursor:]
    if after:
        segments.extend(source.text_segments(cursor, len(chunk.text)))
    return NativeParagraph(
        heading_level=source.paragraphs[0].heading if source.paragraphs else None,
        segments=tuple(segments),
    )


def is_answer_line_chunk(chunk: DocxChunk) -> bool:
    """A chunk whose only paragraph is a printed answer line has no question text (W10).

    True only when the chunk renders a paragraph and that whole paragraph is whitespace
    and underscores. A content-less chunk and a chunk that keeps any other wording or
    carries a picture are not answer-line chunks: they still become a review item.
    """
    paragraph = source_paragraph(chunk)
    return paragraph is not None and is_printed_answer_line(paragraph.segments)


def source_paragraphs(chunks: Iterable[DocxChunk]) -> tuple[NativeParagraph, ...]:
    """Every source chunk as one body, in the given order, contentless chunks skipped."""
    result: list[NativeParagraph] = []
    for chunk in chunks:
        if not chunk.paragraphs or len(chunk.paragraphs) == 1:
            paragraph = source_paragraph(chunk)
            if paragraph is not None:
                result.append(paragraph)
            continue
        # Multi-paragraph chunks (for example table cells) retain their block levels.
        source = SourceFormatting((chunk,))
        placements: list[tuple[int, NativeSegment]] = [
            (image.offset, NativeAssetSegment(asset_id=image.asset_id)) for image in chunk.images
        ]
        placements.extend(
            (image.offset, NativeTextSegment(text=_missing_picture_text(image), marks=()))
            for image in chunk.missing_images
        )
        placements.sort(key=lambda entry: entry[0])
        previous_end: int | None = None
        for index, block in enumerate(chunk.paragraphs):
            end = block.offset + len(block.text)
            last = index == len(chunk.paragraphs) - 1
            cursor = block.offset
            segments: list[NativeSegment] = []
            for offset, segment in placements:
                if block.offset <= offset < end or (last and offset == end):
                    segments.extend(source.text_segments(cursor, offset))
                    segments.append(segment)
                    cursor = offset
            segments.extend(source.text_segments(cursor, end))
            if segments:
                separator = (
                    chunk.text[previous_end : block.offset] if previous_end is not None else ""
                )
                if (
                    result
                    and previous_end is not None
                    and separator == " | "
                    and result[-1].heading_level == block.heading_level
                ):
                    result[-1] = result[-1].model_copy(
                        update={
                            "segments": (
                                *result[-1].segments,
                                *source.text_segments(previous_end, block.offset),
                                *segments,
                            )
                        }
                    )
                else:
                    result.append(
                        NativeParagraph(heading_level=block.heading_level, segments=tuple(segments))
                    )
                previous_end = end
    return tuple(result)


def review_source_paragraphs(
    chunks: Iterable[DocxChunk],
) -> tuple[tuple[str, NativeParagraph], ...]:
    """The review fallback body with each paragraph's source chunk.

    Printed answer lines are answer space, not question text (W10), so they are skipped;
    every kept paragraph is paired with the anchor of the chunk that produced it, so the
    review body and its alignment always come from the same render.
    """
    result: list[tuple[str, NativeParagraph]] = []
    for chunk in chunks:
        result.extend(
            (chunk.anchor, paragraph)
            for paragraph in source_paragraphs((chunk,))
            if not is_printed_answer_line(paragraph.segments)
        )
    return tuple(result)


def body_asset_ids(body: Iterable[NativeParagraph]) -> tuple[str, ...]:
    """Every picture the body places, in reading order, an id repeating as it repeats."""
    return tuple(
        segment.asset_id
        for paragraph in body
        for segment in paragraph.segments
        if isinstance(segment, NativeAssetSegment)
    )


def body_text_lines(body: Iterable[NativeParagraph]) -> tuple[str, ...]:
    """The body as plain text lines with ``[___]`` gap markers, empty lines dropped."""
    lines: list[str] = []
    for paragraph in body:
        parts: list[str] = []
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                parts.append(segment.text)
            elif isinstance(segment, NativeGapSegment):
                parts.append(_GAP_MARKER)
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return tuple(lines)


def body_plain_text(body: Iterable[NativeParagraph]) -> str:
    """The body as one text block, one line per paragraph."""
    return "\n".join(body_text_lines(body))
