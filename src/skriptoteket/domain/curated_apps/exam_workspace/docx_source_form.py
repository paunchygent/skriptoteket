"""A chunk's source form that keeps the response atoms an item placed in it (TASK-SKRIPT-39-04-13).

Section placement shows an instruction an item shows in its source form: its source
paragraphs with marks and pictures. When the item placed a response gap in the paragraphs it
aligned to that chunk, the gap belongs to the item's response contract, which requires every
declared gap exactly once. The source form then carries each gap at its one source location
(``gap_spans``: a printed blank, or the gap's answer in the source text), in place of the text
that location prints.
"""

from collections.abc import Mapping, Sequence

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import source_paragraphs
from skriptoteket.domain.curated_apps.exam_workspace.source_format_gap_alignment import gap_spans


def _text(paragraph: NativeParagraph) -> str:
    return "".join(s.text for s in paragraph.segments if isinstance(s, NativeTextSegment))


def _with_gaps(
    paragraph: NativeParagraph, spans: Sequence[tuple[int, int, NativeGapSegment]]
) -> NativeParagraph:
    """The paragraph with each span of its text replaced by its gap; pictures keep their place."""
    segments: list[NativeSegment] = []
    offset = 0
    for segment in paragraph.segments:
        if not isinstance(segment, NativeTextSegment):
            segments.append(segment)
            continue
        end = offset + len(segment.text)
        cursor = offset
        for start, stop, gap in spans:
            if stop <= cursor or start >= end:
                continue
            if start > cursor:
                segments.append(
                    segment.model_copy(
                        update={"text": segment.text[cursor - offset : start - offset]}
                    )
                )
            if start >= offset:
                segments.append(gap)
            cursor = min(stop, end)
        if cursor < end:
            segments.append(segment.model_copy(update={"text": segment.text[cursor - offset :]}))
        offset = end
    return paragraph.model_copy(update={"segments": tuple(segments)})


def source_form(
    chunk: DocxChunk,
    shown: Sequence[NativeParagraph],
    answers: Mapping[str, tuple[str, ...]],
) -> tuple[NativeParagraph, ...] | None:
    """The chunk's source paragraphs, carrying each gap of ``shown`` at its source location.

    ``shown`` are the item's paragraphs aligned to the chunk and ``answers`` each gap's
    accepted values. None when a gap has no unique source location inside one paragraph: the
    source form cannot then carry the item's response.
    """
    paragraphs = source_paragraphs((chunk,))
    gaps = [s for p in shown for s in p.segments if isinstance(s, NativeGapSegment)]
    if not gaps:
        return paragraphs
    texts = [_text(paragraph) for paragraph in paragraphs]
    found = gap_spans("\n".join(texts), gaps, dict(answers))
    if found is None:
        return None
    placed: list[list[tuple[int, int, NativeGapSegment]]] = [[] for _ in paragraphs]
    for (start, stop), gap in zip(found, gaps, strict=True):
        begin = 0
        for index, text in enumerate(texts):
            if begin <= start and stop <= begin + len(text):
                placed[index].append((start - begin, stop - begin, gap))
                break
            begin += len(text) + 1
        else:
            return None
    return tuple(
        _with_gaps(paragraph, spans) if spans else paragraph
        for paragraph, spans in zip(paragraphs, placed, strict=True)
    )
