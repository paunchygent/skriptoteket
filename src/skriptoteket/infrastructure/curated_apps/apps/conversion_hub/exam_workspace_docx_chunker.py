"""Segment DOCX body blocks, text or drawn, without interpreting exam content."""

import io
import zipfile
from collections.abc import Iterator
from dataclasses import replace

from docx import Document
from docx.document import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.table import Table, _Cell
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxMissingImage,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_picture import (  # noqa: E501
    picture_from_relationship,
)

# Drawn content: pictures, text boxes and embedded objects. Its words, if any, are not in
# the block's plain text, so a block holding only drawn content is still source.
DRAWN = tuple(qn(tag) for tag in ("w:drawing", "w:pict", "w:object", "w:txbxContent"))
_BLIP = qn("a:blip")
_EMBED = qn("r:embed")
_LINK = qn("r:link")
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_RPR = qn("w:rPr")
_RUN_TEXT_TAGS = frozenset(
    qn(tag) for tag in ("w:br", "w:cr", "w:noBreakHyphen", "w:ptab", "w:t", "w:tab")
)
_TXBX = qn("w:txbxContent")
_V_IMAGEDATA = "{urn:schemas-microsoft-com:vml}imagedata"
_V_ID = qn("r:id")
_V_HREF = qn("r:href")


def drawn(element: BaseOxmlElement) -> bool:
    return any(next(element.iter(tag), None) is not None for tag in DRAWN)


def _picture_refs(element: BaseOxmlElement) -> Iterator[tuple[str | None, BaseOxmlElement]]:
    """Picture ids and their blip/imagedata nodes inside one drawing or pict, in order.

    Text-box content is drawn, not flowed text, so its nested pictures are not refs of
    the paragraph's own picture place. The exact node travels with the id so the shared
    normalizer can inspect its nearest ``pic:pic`` for a crop, flip or rotation. A node
    without an embedded or linked id still travels, so its missing relationship becomes a
    named descriptor instead of a silently dropped picture.
    """
    for child in element:
        if child.tag in (_TXBX, _MC_FALLBACK):
            continue
        if child.tag == _BLIP:
            yield child.get(_EMBED) or child.get(_LINK), child
        elif child.tag == _V_IMAGEDATA:
            yield child.get(_V_ID) or child.get(_V_HREF), child
        else:
            yield from _picture_refs(child)


def _png_size(payload: bytes) -> tuple[int | None, int | None]:
    """A PNG's pixel size when it is readable, else nulls."""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return int(image.width), int(image.height)
    except (OSError, ValueError):
        return None, None


def _run_images(
    run: Run, document: DocxDocument
) -> tuple[tuple[int, DocxImage | DocxMissingImage], ...]:
    """Each picture in one run with its offset in ``run.text``, in run order.

    The offset counts every run content that carries text (``w:t``, tab, line break,
    no-break hyphen), exactly like ``Run.text``; the same picture used twice is two
    pictures. An ``mc:Fallback`` duplicate of an ``mc:Choice`` drawing is not a second
    picture.
    """
    found: list[tuple[int, DocxImage | DocxMissingImage]] = []
    text_length = 0
    for child in run._r:
        if child.tag in _RUN_TEXT_TAGS:
            text_length += len(str(child))
            continue
        if child.tag == _RPR:
            continue
        for rid, node in _picture_refs(child):
            found.append((text_length, picture_from_relationship(document, rid, element=node)))
    return tuple(found)


def _paragraph_render(
    paragraph: Paragraph, document: DocxDocument
) -> tuple[str, str, tuple[tuple[int, int, DocxImage | DocxMissingImage], ...]]:
    """A paragraph's plain text, its marked text, and each picture's place in both.

    ``plain`` matches ``Paragraph.text`` (runs and hyperlink runs, tabs and line breaks);
    ``marked`` wraps italic stretches in ``<i>...</i>`` exactly as the model sees them.
    Positions are the characters before the picture in each rendering.
    """
    plain_parts: list[str] = []
    stretches: list[tuple[bool, str, list[tuple[int, DocxImage | DocxMissingImage, int]]]] = []
    plain_length = 0
    for content in paragraph.iter_inner_content():
        runs = content.runs if isinstance(content, Hyperlink) else (content,)
        for run in runs:
            run_images = _run_images(run, document)
            italic = bool(run.italic)
            if not stretches or stretches[-1][0] != italic:
                stretches.append((italic, "", []))
            state, stretch_text, stretch_images = stretches[-1]
            base = len(stretch_text)
            stretch_images.extend(
                (base + offset, image, plain_length + offset) for offset, image in run_images
            )
            stretches[-1] = (state, stretch_text + run.text, stretch_images)
            # ``Paragraph.text`` joins every run and hyperlink, so plain offsets count both.
            plain_parts.append(run.text)
            plain_length += len(run.text)
    marked_parts: list[str] = []
    positions: list[tuple[int, int, DocxImage | DocxMissingImage]] = []
    marked_length = 0
    for italic, text, placements in stretches:
        core = text.strip()
        if italic and core:
            start = text.index(core)
            marked = f"{text[:start]}<i>{core}</i>{text[start + len(core) :]}"
            for offset, image, plain_offset in placements:
                shift = 0 if offset <= start else (3 if offset <= start + len(core) else 7)
                positions.append((plain_offset, marked_length + offset + shift, image))
        else:
            marked = text
            positions.extend(
                (plain_offset, marked_length + offset, image)
                for offset, image, plain_offset in placements
            )
        marked_parts.append(marked)
        marked_length += len(marked)
    return "".join(plain_parts), "".join(marked_parts), tuple(positions)


def _table_render(
    table: Table, document: DocxDocument
) -> tuple[str, str, tuple[tuple[int, int, DocxImage | DocxMissingImage], ...]]:
    """A table's plain text, its marked text, and picture places, in one walk.

    Cells join with `` | `` and rows with a newline, exactly like the text projection;
    every picture keeps its place in that joined text.
    """
    plain_parts: list[str] = []
    marked_parts: list[str] = []
    positions: list[tuple[int, int, DocxImage | DocxMissingImage]] = []
    plain_length = 0
    marked_length = 0
    has_text = False

    def add(
        plain: str,
        marked: str,
        images: tuple[tuple[int, int, DocxImage | DocxMissingImage], ...],
        *,
        counts: bool = False,
    ) -> None:
        nonlocal plain_length, marked_length, has_text
        positions.extend(
            (plain_length + plain_offset, marked_length + marked_offset, image)
            for plain_offset, marked_offset, image in images
        )
        plain_parts.append(plain)
        marked_parts.append(marked)
        plain_length += len(plain)
        marked_length += len(marked)
        # Cell and row separators are layout, never content: only a block's own text counts.
        has_text = has_text or (counts and bool(plain.strip()))

    for row_index, row in enumerate(table.rows):
        if row_index:
            add("\n", "\n", ())
        for cell_index, element in enumerate(row._tr.tc_lst):
            if cell_index:
                add(" | ", " | ", ())
            cell = _Cell(element, table)
            for block_index, block in enumerate(cell.iter_inner_content()):
                if block_index:
                    add("\n", "\n", ())
                if isinstance(block, Paragraph):
                    add(*_paragraph_render(block, document), counts=True)
                else:
                    add(*_table_render(block, document), counts=True)
    if not has_text:
        return "", "", tuple((0, 0, image) for _, _, image in positions)
    return "".join(plain_parts), "".join(marked_parts), tuple(positions)


def _rendered_picture(
    document: DocxDocument,
    element: CT_P | CT_Tbl,
    missing: DocxMissingImage,
    *,
    anchor: str,
) -> DocxImage | None:
    """The whole block as one PNG at the missing picture's place, or None when unavailable."""
    payload = _block_png(document, element, anchor=anchor)
    if payload is None:
        return None
    width, height = _png_size(payload)
    return DocxImage(
        payload=payload,
        media_type="image/png",
        offset=missing.offset,
        marked_offset=missing.marked_offset,
        width=width,
        height=height,
    )


def _block_png(document: DocxDocument, element: CT_P | CT_Tbl, *, anchor: str) -> bytes | None:
    """The labeler renderer's whole-block PNG, or None when it cannot draw the block.

    Imported here because the renderer's WeasyPrint and pypdfium2 stack is heavy and only
    this rare path needs it. Its documented failure means the block has no faithful image,
    so the caller keeps the picture's named descriptor.
    """
    from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
        DocxBlockImageRenderer,
        LabelerSourceImageUnavailable,
    )

    try:
        return DocxBlockImageRenderer(document).render(element, anchor=anchor)
    except LabelerSourceImageUnavailable:
        return None


def _placeable_pictures(
    document: DocxDocument,
    element: CT_P | CT_Tbl,
    text: str,
    positions: tuple[tuple[int, int, DocxImage | DocxMissingImage], ...],
    *,
    anchor: str,
) -> tuple[tuple[DocxImage, ...], tuple[DocxMissingImage, ...]]:
    """Split a block's pictures into usable images and named missing ones.

    An image-only block whose only picture is missing is rendered whole by the labeler's
    block renderer; its PNG then takes that picture's exact place and no descriptor remains.
    A block with text or a usable picture keeps the descriptor instead: a whole-block render
    would duplicate that text or picture, which is not the source.
    """
    placed = tuple(
        replace(picture, offset=offset, marked_offset=marked_offset)
        for offset, marked_offset, picture in positions
    )
    images = tuple(picture for picture in placed if isinstance(picture, DocxImage))
    missing = tuple(picture for picture in placed if isinstance(picture, DocxMissingImage))
    if not text.strip() and not images and len(missing) == 1:
        rendered = _rendered_picture(document, element, missing[0], anchor=anchor)
        if rendered is not None:
            return (rendered,), ()
    return images, missing


class PythonDocxExamChunker:
    """Keep body order, source whitespace and stable body-child anchors."""

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]:
        chunks: list[DocxChunk] = []
        try:
            document = Document(io.BytesIO(content))
            for ordinal, element in enumerate(document.element.body, start=1):
                anchor = f"body:{ordinal:04d}"
                if isinstance(element, CT_P):
                    paragraph = Paragraph(element, document)
                    text, marked_text, positions = _paragraph_render(paragraph, document)
                    style_name = paragraph.style.name if paragraph.style is not None else ""
                    kind = "heading" if style_name.startswith(("Heading", "Title")) else "paragraph"
                    if not text.strip() and drawn(element):
                        kind = "drawing"
                    block: CT_P | CT_Tbl = element
                elif isinstance(element, CT_Tbl):
                    table = Table(element, document)
                    text, marked_text, positions = _table_render(table, document)
                    kind = "table"
                    block = element
                else:
                    continue
                if text.strip() or drawn(element):
                    images, missing = _placeable_pictures(
                        document, block, text, positions, anchor=anchor
                    )
                    chunks.append(
                        DocxChunk(
                            anchor=anchor,
                            kind=kind,
                            text=text,
                            marked_text=marked_text,
                            images=images,
                            missing_images=missing,
                        )
                    )
        except (
            PackageNotFoundError,
            zipfile.BadZipFile,
            SyntaxError,
            KeyError,
            ValueError,
            OSError,
            AttributeError,
        ) as error:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Filen kunde inte läsas som ett Word-dokument (.docx).",
            ) from error

        if not chunks:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Word-dokumentet saknar läsbart innehåll.",
            )
        return tuple(chunks)
