"""Rebuild the Word import's chunks from one PDF's laid-out lines (ST-SKRIPT-39-10 P5).

The blocks are the ones the Word chunker produces, so the existing Word conversion path
runs on them unchanged:

- Paragraphs and headings: grouped and rendered by ``exam_workspace_pdf_paragraphs``.
- Tables: found and rendered by ``exam_workspace_pdf_block_tables``.
- Pictures: a cut picture or figure is a chunk of its own, ``kind="drawing"`` with empty
  text and the picture, as the Word chunker gives a paragraph holding only a picture.

Each block carries its labeler markdown in the Word labeler's form: ``#`` headings,
``**bold**``, ``- `` bullets and GFM tables.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_block_tables import (  # noqa: E501
    table_block,
    with_borderless_tables,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfLine,
    PdfTable,
    body_points,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_paragraphs import (  # noqa: E501
    Paragraph,
    heading_levels,
    line_spacing,
    paragraphs_of,
    render,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_pictures import (  # noqa: E501
    PdfBlockItem,
    PdfPicture,
)


@dataclass(frozen=True)
class PdfBlock:
    """One rebuilt block: the Word-shaped chunk and its labeler markdown (D14)."""

    chunk: DocxChunk
    markdown: str


def pdf_blocks(items: Sequence[PdfBlockItem]) -> tuple[PdfBlock, ...]:
    """Every block in reading order, anchored ``body:0001`` onward like the Word chunker."""
    spacing = line_spacing(items)
    body_size = body_points(
        word for item in items if isinstance(item, PdfLine) for word in item.words
    )
    left = min((item.x0 for item in items if isinstance(item, PdfLine)), default=0.0)
    # Consecutive lines group into paragraphs; a table or a picture always stands alone.
    sequence: list[Paragraph | PdfTable | PdfPicture] = []
    pending: list[PdfLine] = []
    for item in [*with_borderless_tables(items, spacing), None]:
        if isinstance(item, PdfLine):
            pending.append(item)
            continue
        sequence.extend(paragraphs_of(pending, spacing))
        pending = []
        if item is not None:
            sequence.append(item)
    levels = heading_levels(
        [entry for entry in sequence if isinstance(entry, Paragraph)], body_size
    )
    blocks: list[PdfBlock] = []
    paragraph_index = -1
    for entry in sequence:
        anchor = f"body:{len(blocks) + 1:04d}"
        if isinstance(entry, PdfPicture):
            picture = entry.picture
            chunk = DocxChunk(
                anchor=anchor,
                kind="drawing",
                text="",
                marked_text="",
                images=(picture,) if isinstance(picture, DocxImage) else (),
                missing_images=() if isinstance(picture, DocxImage) else (picture,),
                paragraphs=(DocxSourceParagraph(offset=0, text=""),),
            )
            blocks.append(PdfBlock(chunk=chunk, markdown=""))
            continue
        if isinstance(entry, PdfTable):
            text, marked, markdown, paragraphs, runs = table_block(entry, spacing)
            if not text.replace("|", "").strip():
                continue
            chunk = DocxChunk(
                anchor=anchor,
                kind="table",
                text=text,
                marked_text=marked,
                runs=tuple(runs),
                paragraphs=tuple(paragraphs),
            )
            blocks.append(PdfBlock(chunk=chunk, markdown=markdown))
            continue
        paragraph_index += 1
        rendered = render(entry, left=left)
        if not rendered.text.strip():
            continue
        level = levels.get(paragraph_index)
        chunk = DocxChunk(
            anchor=anchor,
            kind="heading" if level is not None else "paragraph",
            text=rendered.text,
            marked_text=rendered.marked,
            runs=rendered.runs,
            paragraphs=(DocxSourceParagraph(offset=0, text=rendered.text, heading_level=level),),
        )
        markdown = rendered.markdown
        if level is not None:
            markdown = "#" * level + " " + markdown.lstrip()
        blocks.append(PdfBlock(chunk=chunk, markdown=markdown))
    return tuple(blocks)
