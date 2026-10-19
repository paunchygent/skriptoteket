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
from itertools import groupby

from skriptoteket.domain.curated_apps.exam_conversion import (
    exam_print_house_template as house_template,
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

_VARIANT_TITLE_SUFFIX: Mapping[house_template.ExamPrintVariant, str] = {
    house_template.ExamPrintVariant.STUDENT: "Elevexemplar",
    house_template.ExamPrintVariant.FACIT: "Facit",
}
_MISSING_IMAGE_MESSAGE = "PDF-exporten saknar bilddata för en bild."


def _font_family_css() -> str:
    """The house font stack: the template's families, each quoted, then a generic fallback."""
    families = ", ".join(f'"{family}"' for family in house_template.HOUSE_FONT_FAMILIES)
    return f"{families}, sans-serif"


def _block_margin_css(spacing: house_template.BlockSpacing) -> str:
    """One block's space before and after as a CSS margin shorthand; side margins stay zero."""
    return f"{spacing.space_before_mm}mm 0 {spacing.space_after_mm}mm"


def _heading_rules() -> str:
    """One CSS rule per heading level the template declares, kept with the next block."""
    template = house_template
    return "\n".join(
        f"h{level} {{ font-size: {template.HEADING_GEOMETRY[level].size_pt}pt;"
        f" margin: {_block_margin_css(template.HEADING_GEOMETRY[level].spacing)};"
        f" font-weight: bold; color: #{template.TEXT_COLOR_HEX}; break-after: avoid }}"
        for level in sorted(template.HEADING_GEOMETRY)
    )


def _house_css() -> str:
    """The house template as CSS, read from the template module's current measures."""
    template = house_template
    return f"""
@page {{
  size: {template.PAGE_WIDTH_MM}mm {template.PAGE_HEIGHT_MM}mm;
  margin: {template.PAGE_MARGIN_VERTICAL_MM}mm {template.PAGE_MARGIN_SIDE_MM}mm;
}}
body {{
  margin: 0;
  padding: 0;
  color: #{template.TEXT_COLOR_HEX};
  font-family: {_font_family_css()};
  font-size: {template.HOUSE_FONT_SIZE_PT}pt;
  line-height: {template.HOUSE_LINE_HEIGHT};
}}
{_heading_rules()}
p {{ margin: {_block_margin_css(template.PARAGRAPH_SPACING)}; break-inside: avoid }}
.print-question {{ margin: 0 0 {template.QUESTION_SPACE_AFTER_MM}mm }}
.print-question-text {{ break-inside: avoid }}
.print-options {{ break-inside: avoid }}
.print-instruction {{
  margin: 0 0 {template.INSTRUCTION_SPACE_AFTER_MM}mm;
  break-inside: avoid;
  break-after: avoid;
}}
p.print-gap_line {{ line-height: {template.WRITING_LINE_PITCH_MM}mm }}
.gap-blank {{
  display: inline-block;
  border-bottom: {template.RULE_WEIGHT_PT}pt solid #{template.RULE_COLOR_HEX};
  height: 1.1em;
  vertical-align: baseline;
}}
.writing-area {{ margin: {_block_margin_css(template.WRITING_AREA_SPACING)} }}
.writing-line {{
  height: {template.WRITING_LINE_PITCH_MM}mm;
  border-bottom: {template.RULE_WEIGHT_PT}pt solid #{template.RULE_COLOR_HEX};
  break-inside: avoid;
}}
.print-option {{ margin: {_block_margin_css(template.OPTION_SPACING)} }}
.number-box {{
  border: {template.BOX_BORDER_PT}pt solid #{template.TEXT_COLOR_HEX};
  display: inline-block;
  width: {template.NUMBER_BOX_WIDTH_MM}mm;
  height: 1.2em;
  vertical-align: middle;
  margin-right: {template.BOX_GAP_MM}mm;
}}
.print-grid {{
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  break-inside: avoid;
  margin: {_block_margin_css(template.GRID_SPACING)};
}}
.print-grid tr {{ break-inside: avoid }}
.print-grid th, .print-grid td {{
  border: {template.RULE_WEIGHT_PT}pt solid #{template.TEXT_COLOR_HEX};
  padding: {template.GRID_CELL_PADDING_MM}mm;
  overflow-wrap: anywhere;
}}
.print-grid td {{ text-align: center }}
.print-grid th[scope="row"] {{ text-align: left }}
.print-answer-key {{
  border-left: {template.ANSWER_KEY_RULE_PT}pt solid #{template.TEXT_COLOR_HEX};
  padding-left: {template.ANSWER_KEY_INDENT_MM}mm;
  margin: {_block_margin_css(template.ANSWER_KEY_SPACING)};
  break-inside: avoid;
  font-weight: bold;
}}
.print-image {{
  display: block;
  max-width: 100%;
  margin: {_block_margin_css(template.IMAGE_SPACING)};
}}
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
        f"<style>{_house_css()}</style>\n"
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
            f'<div class="print-question-text">\n{self._blocks(entry.text)}\n</div>\n'
            f"{self._answer_blocks(entry.answer)}\n"
            "</section>"
        )

    def _answer_blocks(self, blocks: tuple[PrintBlock, ...]) -> str:
        """The answer form: each run of options wrapped in its own keep-together div."""
        parts: list[str] = []
        for is_option, run in groupby(blocks, key=lambda block: isinstance(block, PrintOption)):
            rendered = self._blocks(tuple(run))
            parts.append(
                f'<div class="print-options">\n{rendered}\n</div>' if is_option else rendered
            )
        return "\n".join(parts)

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
            box, label = house_template.TICK_BOX_GLYPH, option.label
        else:
            box, label = '<span class="number-box"></span>', ""
        prefix = f"{escape(label)} " if label else ""
        return f'<p class="print-option">{box} {prefix}{escape(option.text)}</p>'

    def _grid(self, grid: PrintGrid) -> str:
        columns = "".join(f'<th scope="col">{escape(column)}</th>' for column in grid.columns)
        head = f"<tr><td></td>{columns}</tr>"
        cell = f"<td>{house_template.TICK_BOX_GLYPH}</td>"
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
