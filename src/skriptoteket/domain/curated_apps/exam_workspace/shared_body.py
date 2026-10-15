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
    - Imports only the body leaf and the DOCX chunk record, so nothing here can cycle
      back into the document or parent models.
"""

from __future__ import annotations

from collections.abc import Iterable

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

_GAP_MARKER = "[___]"


def _missing_picture_text(missing: DocxMissingImage) -> str:
    return f"[Bild saknas: {missing.reference} ({missing.media_type})]"


def source_paragraph(chunk: DocxChunk) -> NativeParagraph | None:
    """One source chunk as a native paragraph, each picture at its exact source place.

    A picture the chunker could not turn into a ``DocxImage`` has no payload, so its exact
    place holds a named text placeholder instead: the teacher sees which picture is missing
    and where, and a picture-only chunk still becomes a non-empty paragraph. A text-less
    chunk without pictures becomes nothing.
    """
    placements: list[tuple[int, NativeSegment]] = [
        (image.offset, NativeAssetSegment(asset_id=image.asset_id)) for image in chunk.images
    ]
    placements.extend(
        (missing.offset, NativeTextSegment(text=_missing_picture_text(missing)))
        for missing in chunk.missing_images
    )
    if not placements:
        if not chunk.text:
            return None
        return NativeParagraph(segments=(NativeTextSegment(text=chunk.text),))
    placements.sort(key=lambda placement: placement[0])
    segments: list[NativeSegment] = []
    cursor = 0
    for offset, segment in placements:
        before = chunk.text[cursor:offset]
        if before:
            segments.append(NativeTextSegment(text=before))
        segments.append(segment)
        cursor = offset
    after = chunk.text[cursor:]
    if after:
        segments.append(NativeTextSegment(text=after))
    return NativeParagraph(segments=tuple(segments))


def source_paragraphs(chunks: Iterable[DocxChunk]) -> tuple[NativeParagraph, ...]:
    """Every source chunk as one body, in the given order, contentless chunks skipped."""
    return tuple(
        paragraph for chunk in chunks if (paragraph := source_paragraph(chunk)) is not None
    )


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
