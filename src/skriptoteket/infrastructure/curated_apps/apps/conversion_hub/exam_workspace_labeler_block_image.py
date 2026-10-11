"""Image of one DOCX body block for the item-type labeler (D14).

Purpose:
    Content that markdown cannot carry faithfully goes to the labeler as an image of that
    block. This module renders one body paragraph or table (pictures, VML previews, text
    boxes, merged cells, nested tables and Word-generated list numbers) to HTML, prints it
    with WeasyPrint on one tall page, rasterizes that page with pypdfium2 and crops it to
    the drawn content. A block that cannot be imaged faithfully raises
    ``LabelerSourceImageUnavailable``.

Relationships:
    ``PythonDocxLabelerMarkdown`` calls ``DocxBlockImageRenderer.render`` for each block
    that needs an image and ``list_label`` for the number Word shows before a paragraph.
"""

from __future__ import annotations

import base64
import html
import io
import re
from collections.abc import Iterator

import pypdfium2  # type: ignore[import-untyped]
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.styles.style import CharacterStyle
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes

_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_V_IMAGEDATA = "{urn:schemas-microsoft-com:vml}imagedata"
_P, _TBL, _TR, _TC = qn("w:p"), qn("w:tbl"), qn("w:tr"), qn("w:tc")
_TXBX = qn("w:txbxContent")
# Paragraph children whose runs Word shows; w:del (deleted text) and w:pPr are not shown.
_RUN_CONTAINERS = frozenset(
    qn(tag)
    for tag in ("w:hyperlink", "w:ins", "w:smartTag", "w:sdt", "w:sdtContent", "w:fldSimple")
)
_WEB_IMAGES = frozenset({"image/png", "image/jpeg", "image/gif"})
_EMU_PER_PX = 9525
_TAB = "&#160;" * 4
_CROP_MARGIN = 16
_CSS = (
    "@page { size: 180mm 1200mm; margin: 5mm } "
    "body { font-family: sans-serif; font-size: 11pt; margin: 0 } "
    "div.p { white-space: pre-wrap; margin: 0 0 4pt 0 } "
    "td { border: 1px solid #000; padding: 2px 4px; vertical-align: top }"
)
_ROMAN = (
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
    (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
)  # fmt: skip


class LabelerSourceImageUnavailable(Exception):
    """No faithful image of the source block can be produced."""

    def __init__(self, anchor: str, reason: str) -> None:
        self.anchor = anchor
        self.reason = reason
        super().__init__(f"No source image for {anchor}: {reason}")


class UnknownListNumberFormat(ValueError):
    """Word numbers this paragraph in a format this renderer cannot reproduce."""

    def __init__(self, number_format: str) -> None:
        self.number_format = number_format
        super().__init__(f"numbering format {number_format}")


class _Unrenderable(Exception):
    """Block content without a faithful HTML rendering; ``render`` adds the anchor."""


def _child(element: BaseOxmlElement | None, tag: str) -> BaseOxmlElement | None:
    return None if element is None else element.find(qn(tag))


def _val(element: BaseOxmlElement | None, attribute: str = "w:val") -> str | None:
    return None if element is None else element.get(qn(attribute))


def _style_chain(style: CharacterStyle | None) -> Iterator[CharacterStyle]:
    """Yield a style and its bases; Word ignores a basedOn cycle, so stop at a repeat."""
    seen: set[str | None] = set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        yield style
        style = style.base_style


def _shown_paragraphs(element: BaseOxmlElement) -> Iterator[BaseOxmlElement]:
    """Yield paragraphs in document order once each; mc:Fallback repeats mc:Choice content."""
    for child in element:
        if child.tag == f"{_MC}Fallback":
            continue
        if child.tag == _P:
            yield child
        yield from _shown_paragraphs(child)


def _format_number(value: int, number_format: str) -> str:
    if number_format == "decimal":
        return str(value)
    if number_format == "decimalZero":
        return f"{value:02d}"
    if number_format in ("lowerLetter", "upperLetter"):
        # Word repeats the letter past z: 27 -> aa, 28 -> bb.
        letters = chr(ord("a") + (value - 1) % 26) * ((value - 1) // 26 + 1)
        return letters if number_format == "lowerLetter" else letters.upper()
    if number_format in ("lowerRoman", "upperRoman"):
        numeral = ""
        for amount, symbol in _ROMAN:
            count, value = divmod(value, amount)
            numeral += symbol * count
        return numeral if number_format == "lowerRoman" else numeral.upper()
    raise UnknownListNumberFormat(number_format)


def _start(level: BaseOxmlElement | None) -> int:
    return int(_val(_child(level, "w:start")) or 1)


class DocxBlockImageRenderer:
    """Render single DOCX body blocks to cropped PNG images."""

    def __init__(self, document: DocxDocument) -> None:
        self._document = document
        self._labels: dict[BaseOxmlElement, str] = {}
        self._unknown: dict[BaseOxmlElement, str] = {}
        counters: dict[str, dict[int, int]] = {}
        used: set[tuple[str, int]] = set()
        for paragraph in _shown_paragraphs(document.element.body):
            resolved = self._numbering(paragraph)
            if resolved is None:
                continue
            num_id, abstract_id, ilvl, levels, override = resolved
            counts = counters.setdefault(abstract_id, {})
            if override is not None and (num_id, ilvl) not in used:
                counts[ilvl] = override
            elif ilvl in counts:
                counts[ilvl] += 1
            else:
                counts[ilvl] = _start(levels.get(ilvl))
            used.add((num_id, ilvl))
            for deeper in [k for k in counts if k > ilvl]:
                del counts[deeper]
            try:
                self._labels[paragraph] = self._label(levels, ilvl, counts)
            except UnknownListNumberFormat as error:
                self._unknown[paragraph] = error.number_format

    def _numbering(
        self, p: BaseOxmlElement
    ) -> tuple[str, str, int, dict[int, BaseOxmlElement], int | None] | None:
        """Resolve numPr like Word: paragraph pPr first, then the paragraph style chain."""
        properties = _child(_child(p, "w:pPr"), "w:numPr")
        if properties is None:
            for style in _style_chain(Paragraph(p, self._document).style):
                properties = _child(_child(style.element, "w:pPr"), "w:numPr")
                if properties is not None:
                    break
        num_id = _val(_child(properties, "w:numId"))
        if num_id is None or num_id == "0":
            return None
        ilvl = int(_val(_child(properties, "w:ilvl")) or 0)
        numbering: BaseOxmlElement = self._document.part.numbering_part.element
        instance = next(n for n in numbering.findall(qn("w:num")) if _val(n, "w:numId") == num_id)
        abstract_id = _val(_child(instance, "w:abstractNumId")) or ""
        abstract = next(
            a
            for a in numbering.findall(qn("w:abstractNum"))
            if _val(a, "w:abstractNumId") == abstract_id
        )
        levels = {int(_val(lvl, "w:ilvl") or 0): lvl for lvl in abstract.findall(qn("w:lvl"))}
        override = next(
            (
                int(_val(_child(o, "w:startOverride")) or 1)
                for o in instance.findall(qn("w:lvlOverride"))
                if _val(o, "w:ilvl") == str(ilvl) and _child(o, "w:startOverride") is not None
            ),
            None,
        )
        return num_id, abstract_id, ilvl, levels, override

    @staticmethod
    def _label(levels: dict[int, BaseOxmlElement], ilvl: int, counts: dict[int, int]) -> str:
        level = levels.get(ilvl)
        number_format = _val(_child(level, "w:numFmt")) or "decimal"
        if number_format == "bullet":
            return "•"
        if number_format == "none":
            return ""

        def number(match: re.Match[str]) -> str:
            k = int(match.group(1)) - 1
            source = levels.get(k)
            value = counts.get(k, _start(source))
            return _format_number(value, _val(_child(source, "w:numFmt")) or "decimal")

        return re.sub(r"%([1-9])", number, _val(_child(level, "w:lvlText")) or "")

    def list_label(self, paragraph: CT_P) -> str | None:
        """Return the list label Word shows, or None when the paragraph is not numbered.

        Raises:
            UnknownListNumberFormat: Word numbers it in a format this renderer cannot show.
        """
        if paragraph in self._unknown:
            raise UnknownListNumberFormat(self._unknown[paragraph])
        return self._labels.get(paragraph)

    def render(self, element: CT_P | CT_Tbl, *, anchor: str) -> bytes:
        """Return PNG bytes of one body paragraph or table, cropped to its drawn content."""
        try:
            fragment = self._block(element)
        except UnknownListNumberFormat as error:
            raise LabelerSourceImageUnavailable(anchor, str(error)) from error
        except _Unrenderable as error:
            raise LabelerSourceImageUnavailable(anchor, str(error)) from error
        page = (
            '<!doctype html><html><head><meta charset="utf-8">'
            f"<style>{_CSS}</style></head><body>{fragment}</body></html>"
        )
        pdf = pypdfium2.PdfDocument(render_html_to_pdf_bytes(html=page))
        try:
            if len(pdf) != 1:
                raise LabelerSourceImageUnavailable(anchor, "block taller than one page")
            image = pdf[0].render(scale=2).to_pil().convert("RGB")
        finally:
            pdf.close()
        box = image.convert("L").point(lambda v: 255 if v < 250 else 0).getbbox()
        if box is None:
            raise LabelerSourceImageUnavailable(anchor, "empty render")
        left, top, right, bottom = box
        cropped = image.crop(
            (
                max(0, left - _CROP_MARGIN),
                max(0, top - _CROP_MARGIN),
                min(image.width, right + _CROP_MARGIN),
                min(image.height, bottom + _CROP_MARGIN),
            )
        )
        output = io.BytesIO()
        cropped.save(output, format="PNG")
        return output.getvalue()

    def _block(self, element: BaseOxmlElement) -> str:
        if element.tag == _P:
            return self._paragraph(element)
        if element.tag == _TBL:
            return self._table(element)
        return ""

    def _paragraph(self, p: BaseOxmlElement) -> str:
        paragraph = Paragraph(p, self._document)
        label = self.list_label(p)
        prefix = f"{html.escape(label)}&#160;" if label else ""
        body = "".join(self._inline(child, paragraph) for child in p)
        style_name = paragraph.style.name if paragraph.style is not None else ""
        style = ""
        if style_name == "Title":
            style = ' style="font-size:20pt;font-weight:bold"'
        elif style_name.startswith("Heading ") and style_name[8:].isdigit():
            size = max(12, 18 - 2 * (int(style_name[8:]) - 1))
            style = f' style="font-size:{size}pt;font-weight:bold"'
        return f'<div class="p"{style}>{prefix}{body or "&#160;"}</div>'

    def _inline(self, element: BaseOxmlElement, paragraph: Paragraph) -> str:
        if element.tag == qn("w:r"):
            run = Run(element, paragraph)
            text = "".join(self._run_child(child) for child in element)
            if self._font_flag(run, paragraph, "italic"):
                text = f"<i>{text}</i>"
            if self._font_flag(run, paragraph, "bold"):
                text = f"<b>{text}</b>"
            return text
        if element.tag in _RUN_CONTAINERS:
            return "".join(self._inline(child, paragraph) for child in element)
        return ""

    @staticmethod
    def _font_flag(run: Run, paragraph: Paragraph, name: str) -> bool:
        """Resolve bold/italic as Word displays it: run, character style, paragraph style."""
        direct = getattr(run.font, name)
        if direct is not None:
            return bool(direct)
        for style in (*_style_chain(run.style), *_style_chain(paragraph.style)):
            flag = getattr(style.font, name)
            if flag is not None:
                return bool(flag)
        return False

    def _run_child(self, element: BaseOxmlElement) -> str:
        tag = element.tag
        if tag == qn("w:t"):
            return html.escape(element.text or "")
        if tag == qn("w:tab"):
            return _TAB
        if tag in (qn("w:br"), qn("w:cr")):
            return "<br>"
        if tag == qn("w:noBreakHyphen"):
            return "-"
        if tag == f"{_MC}AlternateContent":
            choice = element.find(f"{_MC}Choice")
            return "" if choice is None else "".join(self._run_child(c) for c in choice)
        if tag == qn("w:drawing"):
            return self._drawing(element)
        if tag in (qn("w:pict"), qn("w:object")):
            return self._vml(element, "object" if tag == qn("w:object") else "VML picture")
        return ""

    def _drawing(self, drawing: BaseOxmlElement) -> str:
        boxes = list(drawing.iter(_TXBX))
        if boxes:
            return "".join(self._text_box(box) for box in boxes)
        blip = next(drawing.iter(qn("a:blip")), None)
        if blip is None:
            data = next(drawing.iter(qn("a:graphicData")), None)
            kind = None if data is None else data.get("uri")
            raise _Unrenderable(f"drawing without a picture ({kind or 'unknown'})")
        extent = next(drawing.iter(qn("wp:extent")), None)
        return self._image(blip.get(f"{_R}embed"), extent)

    def _vml(self, element: BaseOxmlElement, what: str) -> str:
        boxes = list(element.iter(_TXBX))
        if boxes:
            return "".join(self._text_box(box) for box in boxes)
        data = next(element.iter(_V_IMAGEDATA), None)
        if data is None:
            raise _Unrenderable(f"{what} without a preview picture")
        return self._image(data.get(f"{_R}id"), None)

    def _image(self, rid: str | None, extent: BaseOxmlElement | None) -> str:
        parts = self._document.part.related_parts
        if rid is None or rid not in parts:
            raise _Unrenderable("picture without an embedded image")
        part = parts[rid]
        if part.content_type not in _WEB_IMAGES:
            raise _Unrenderable(f"picture of type {part.content_type}")
        size = ""
        if extent is not None:
            width = int(extent.get("cx") or 0) / _EMU_PER_PX
            height = int(extent.get("cy") or 0) / _EMU_PER_PX
            size = f' style="width:{width:.2f}px;height:{height:.2f}px"'
        encoded = base64.b64encode(part.blob).decode("ascii")
        return f'<img src="data:{part.content_type};base64,{encoded}"{size}>'

    def _text_box(self, box: BaseOxmlElement) -> str:
        inner = "".join(self._block(child) for child in box)
        return f'<div style="border:1px solid #000;padding:4px">{inner}</div>'

    def _table(self, tbl: BaseOxmlElement) -> str:
        grid: list[dict[int, BaseOxmlElement]] = []
        for tr in tbl.findall(_TR):
            column = int(_val(_child(_child(tr, "w:trPr"), "w:gridBefore")) or 0)
            cells: dict[int, BaseOxmlElement] = {}
            for tc in tr.findall(_TC):
                cells[column] = tc
                column += int(_val(_child(_child(tc, "w:tcPr"), "w:gridSpan")) or 1)
            grid.append(cells)
        rows: list[str] = []
        for index, cells in enumerate(grid):
            rendered: list[str] = []
            for column, tc in cells.items():
                merge = _child(_child(tc, "w:tcPr"), "w:vMerge")
                if merge is not None and _val(merge) != "restart":
                    continue
                attributes = ""
                span = int(_val(_child(_child(tc, "w:tcPr"), "w:gridSpan")) or 1)
                if span > 1:
                    attributes += f' colspan="{span}"'
                if merge is not None:
                    attributes += f' rowspan="{1 + self._continued(grid, index, column)}"'
                content = "".join(self._block(child) for child in tc)
                rendered.append(f"<td{attributes}>{content}</td>")
            rows.append(f"<tr>{''.join(rendered)}</tr>")
        return f'<table style="border-collapse:collapse">{"".join(rows)}</table>'

    @staticmethod
    def _continued(grid: list[dict[int, BaseOxmlElement]], index: int, column: int) -> int:
        """Count rows directly below that continue the vertical merge at this grid column."""
        count = 0
        for cells in grid[index + 1 :]:
            merge = _child(_child(cells.get(column), "w:tcPr"), "w:vMerge")
            if merge is None or _val(merge) not in (None, "continue"):
                break
            count += 1
        return count
