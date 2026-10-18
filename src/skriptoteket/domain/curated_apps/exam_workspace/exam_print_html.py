"""Print PDF HTML for the printed exam house template (TASK-SKRIPT-40-04-07 W1-W9).

Purpose:
    Render one ``PrintDocument`` (student or facit) as one HTML document in the house
    template, ready for WeasyPrint. Print PDF HTML renders only the print document, the
    same content and order as the DOCX student copy; it is not the Exam.net import PDF.

Relationships:
    Reads the format-neutral print document (``exam_print_document``), the fixed house
    template measures (``exam_conversion.exam_print_house_template``) and the stored
    picture payloads declared by ``NativeExamAsset``. Pictures are inlined as data URIs,
    so the renderer needs no files. It is a pure leaf: it renders and returns a string and
    writes nothing back.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping, Sequence
from html import escape

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    HOUSE_FONT_FAMILIES,
    HOUSE_FONT_SIZE_PT,
    HOUSE_LINE_HEIGHT,
    PAGE_MARGIN_SIDE_MM,
    PAGE_MARGIN_VERTICAL_MM,
    WRITING_LINE_PITCH_MM,
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlock,
    PrintBox,
    PrintDocument,
    PrintGrid,
    PrintHeading,
    PrintImage,
    PrintInstruction,
    PrintOption,
    PrintParagraph,
    PrintQuestion,
    PrintRuledLines,
    PrintRun,
    PrintText,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_VARIANT_TITLE_SUFFIX: Mapping[ExamPrintVariant, str] = {
    ExamPrintVariant.STUDENT: "Elevexemplar",
    ExamPrintVariant.FACIT: "Facit",
}
_MISSING_IMAGE_MESSAGE = "PDF-exporten saknar bilddata för en bild."


def _font_family_css() -> str:
    """The house font stack: the template's families, each quoted, then a generic fallback."""
    families = ", ".join(f'"{family}"' for family in HOUSE_FONT_FAMILIES)
    return f"{families}, sans-serif"


_HOUSE_CSS = f"""
@page {{ size: A4; margin: {PAGE_MARGIN_VERTICAL_MM}mm {PAGE_MARGIN_SIDE_MM}mm; }}
body {{
  color: #111;
  font-family: {_font_family_css()};
  font-size: {HOUSE_FONT_SIZE_PT}pt;
  line-height: {HOUSE_LINE_HEIGHT};
}}
h1 {{ font-size: 18pt; margin: 0 0 6mm }}
h3 {{ font-size: 14pt; margin: 0 0 3mm; break-after: avoid }}
p {{ margin: 0 0 2mm }}
.print-question {{ margin: 0 0 8mm }}
.print-instruction {{ margin: 0 0 6mm; break-inside: avoid }}
p.print-gap_line {{ line-height: {WRITING_LINE_PITCH_MM}mm }}
p.print-points {{ font-weight: 700 }}
.gap-blank {{
  display: inline-block;
  border-bottom: 0.8pt solid #111;
  height: 1.1em;
  vertical-align: baseline;
}}
.writing-area {{ margin: 2mm 0 4mm }}
.writing-line {{
  height: {WRITING_LINE_PITCH_MM}mm;
  border-bottom: 0.6pt solid #555;
  break-inside: avoid;
}}
.print-option {{ margin: 0 0 3mm }}
.tick-box {{
  border: 1pt solid #111;
  display: inline-block;
  width: 4mm;
  height: 4mm;
  vertical-align: middle;
  margin-right: 2mm;
}}
.number-box {{
  border: 1pt solid #111;
  display: inline-block;
  width: 9mm;
  height: 6mm;
  vertical-align: middle;
  margin-right: 2mm;
}}
.print-grid {{ border-collapse: collapse; width: 100%; table-layout: fixed; margin: 2mm 0 4mm }}
.print-grid th, .print-grid td {{
  border: 0.5pt solid #111;
  padding: 2mm;
  overflow-wrap: anywhere;
}}
.print-grid td {{ text-align: center }}
.print-grid th[scope="row"] {{ text-align: left }}
.print-answer-key {{
  border-left: 2pt solid #111;
  padding-left: 3mm;
  margin: 2mm 0 4mm;
  break-inside: avoid;
  font-weight: 700;
}}
.print-image {{ display: block; max-width: 100%; margin: 2mm 0 }}
"""


def render_print_html(
    print_document: PrintDocument,
    *,
    assets: Sequence[NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
) -> str:
    """Render ``print_document`` as one house-template HTML document for WeasyPrint.

    Pictures are resolved from ``assets`` (their declared length and sha256) and
    ``assets_by_id`` (their stored bytes) and inlined as data URIs. A referenced picture
    without matching bytes fails closed with a validation error rather than dropping.
    """
    renderer = _PrintHtmlRenderer(assets=assets, assets_by_id=assets_by_id)
    entries = "\n".join(renderer.entry(entry) for entry in print_document.entries)
    suffix = _VARIANT_TITLE_SUFFIX[print_document.variant]
    title = f"{escape(print_document.title)} – {suffix}"
    return (
        "<!doctype html>\n"
        '<html lang="sv">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{title}</title>\n"
        f"<style>{_HOUSE_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        f"{entries}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


class _PrintHtmlRenderer:
    """One render pass: it holds the picture lookup and the data URIs already built."""

    def __init__(
        self, *, assets: Sequence[NativeExamAsset], assets_by_id: Mapping[str, bytes]
    ) -> None:
        self._assets = {asset.asset_id: asset for asset in assets}
        self._assets_by_id = assets_by_id
        self._data_uris: dict[str, str] = {}

    def entry(self, entry: PrintInstruction | PrintQuestion) -> str:
        if isinstance(entry, PrintInstruction):
            return f'<div class="print-instruction">\n{self._blocks(entry.blocks)}\n</div>'
        item_id = escape(entry.item_id, quote=True)
        return (
            f'<section class="print-question" id="exam-item-{item_id}">\n'
            f"{self._blocks(entry.blocks)}\n"
            "</section>"
        )

    def _blocks(self, blocks: tuple[PrintBlock, ...]) -> str:
        return "\n".join(self._block(block) for block in blocks)

    def _block(self, block: PrintBlock) -> str:
        if isinstance(block, PrintHeading):
            return f"<h{block.level}>{escape(block.text)}</h{block.level}>"
        if isinstance(block, PrintParagraph):
            return f'<p class="print-{block.style.value}">{self._runs(block.runs)}</p>'
        if isinstance(block, PrintRuledLines):
            lines = '<div class="writing-line"></div>' * block.count
            return f'<div class="writing-area">{lines}</div>'
        if isinstance(block, PrintOption):
            return self._option(block)
        if isinstance(block, PrintGrid):
            return self._grid(block)
        if isinstance(block, PrintAnswerKey):
            return self._answer_key(block)
        raise AssertionError(f"unhandled print block: {type(block).__name__}")

    def _runs(self, runs: tuple[PrintRun, ...]) -> str:
        return "".join(self._run(run) for run in runs)

    def _run(self, run: PrintRun) -> str:
        if isinstance(run, PrintImage):
            return f'<img class="print-image" src="{self._data_uri(run.asset_id)}" alt="Bild">'
        if isinstance(run, PrintText):
            return escape(run.text)
        return f'<span class="gap-blank" style="width:{run.width_mm:.1f}mm"></span>'

    def _option(self, option: PrintOption) -> str:
        if option.box is PrintBox.TICK:
            box, label = '<span class="tick-box"></span>', option.label
        else:
            box, label = '<span class="number-box"></span>', ""
        prefix = f"{escape(label)} " if label else ""
        return f'<p class="print-option">{box} {prefix}{escape(option.text)}</p>'

    def _grid(self, grid: PrintGrid) -> str:
        columns = "".join(f'<th scope="col">{escape(column)}</th>' for column in grid.columns)
        head = f"<tr><td></td>{columns}</tr>"
        cell = '<td><span class="tick-box"></span></td>'
        rows = "".join(
            f'<tr><th scope="row">{escape(row)}</th>{cell * len(grid.columns)}</tr>'
            for row in grid.rows
        )
        return f'<table class="print-grid"><thead>{head}</thead><tbody>{rows}</tbody></table>'

    def _answer_key(self, key: PrintAnswerKey) -> str:
        lines = "".join(f"<p>{escape(line)}</p>" for line in key.lines)
        return f'<div class="print-answer-key">{lines}</div>'

    def _data_uri(self, asset_id: str) -> str:
        cached = self._data_uris.get(asset_id)
        if cached is not None:
            return cached
        asset = self._assets.get(asset_id)
        payload = self._assets_by_id.get(asset_id)
        if asset is None or payload is None:
            raise _missing_image(asset_id)
        if len(payload) != asset.byte_length or hashlib.sha256(payload).hexdigest() != asset.sha256:
            raise _missing_image(asset_id)
        data_uri = f"data:{asset.media_type};base64,{base64.b64encode(payload).decode('ascii')}"
        self._data_uris[asset_id] = data_uri
        return data_uri


def _missing_image(asset_id: str) -> DomainError:
    return DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message=_MISSING_IMAGE_MESSAGE,
        details={"asset_ids": [asset_id]},
    )
