"""Project source-run offsets through deterministic text deletion/normalization."""

from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting


def projected_chunk(chunk: DocxChunk, text: str, origins: tuple[int, ...]) -> DocxChunk:
    """Each displayed character names its original offset, including collapsed spaces."""
    source = SourceFormatting((chunk,))
    runs: list[DocxSourceRun] = []
    start = 0
    while start < len(text):
        marks = source.marks[origins[start]]
        end = start + 1
        while end < len(text) and source.marks[origins[end]] == marks:
            end += 1
        runs.append(DocxSourceRun(offset=start, text=text[start:end], marks=marks))
        start = end
    heading = chunk.paragraphs[0].heading_level if chunk.paragraphs else None
    paragraphs = (DocxSourceParagraph(offset=0, text=text, heading_level=heading),) if text else ()
    return replace(chunk, text=text, marked_text=text, runs=tuple(runs), paragraphs=paragraphs)
