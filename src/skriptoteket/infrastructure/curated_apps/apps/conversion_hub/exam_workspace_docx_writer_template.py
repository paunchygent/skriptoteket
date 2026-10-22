"""The one house template applied to a Word export (W1, W3).

Purpose:
    ``apply_house_template`` sets the page, the ``Normal`` style and every declared heading
    level of a new python-docx document from ``exam_print_house_template``: A4 with the
    template margins, the house font on all four script slots, the template text colour and
    each style's spacing. Theme fonts and theme colours are removed, so no Word built-in
    layout default survives. ``set_style_spacing`` writes a ``BlockSpacing`` onto a paragraph
    format; the renderer uses it for each printed block.

Relationships:
    - ``exam_print_house_template`` owns every dimension; the print PDF/preview renders the
      same template (W1, ruling 2026-10-18).
    - ``exam_workspace_docx_writer`` applies the template to each new export before it
      renders the student copy.
"""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from docx.styles.style import ParagraphStyle
from docx.text.parfmt import ParagraphFormat

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    HEADING_GEOMETRY,
    HOUSE_FONT_FAMILIES,
    HOUSE_FONT_SIZE_PT,
    HOUSE_LINE_HEIGHT,
    PAGE_HEIGHT_MM,
    PAGE_MARGIN_SIDE_MM,
    PAGE_MARGIN_VERTICAL_MM,
    PAGE_WIDTH_MM,
    PARAGRAPH_SPACING,
    TEXT_COLOR_HEX,
    BlockSpacing,
)


def apply_house_template(output: DocxDocument) -> None:
    """The one house template: A4, the house font and every print style (W1, W3).

    No Word built-in layout default survives: the page, ``Normal`` and every declared
    heading level take their geometry from ``exam_print_house_template``.
    """
    for section in output.sections:
        section.page_width = Mm(PAGE_WIDTH_MM)
        section.page_height = Mm(PAGE_HEIGHT_MM)
        section.left_margin = Mm(PAGE_MARGIN_SIDE_MM)
        section.right_margin = Mm(PAGE_MARGIN_SIDE_MM)
        section.top_margin = Mm(PAGE_MARGIN_VERTICAL_MM)
        section.bottom_margin = Mm(PAGE_MARGIN_VERTICAL_MM)

    normal = output.styles["Normal"]
    _apply_house_font(normal)
    normal.font.size = Pt(HOUSE_FONT_SIZE_PT)
    normal.paragraph_format.line_spacing = HOUSE_LINE_HEIGHT
    _apply_house_text_color(normal)
    set_style_spacing(normal.paragraph_format, PARAGRAPH_SPACING)

    for level, geometry in HEADING_GEOMETRY.items():
        heading = output.styles[f"Heading {level}"]
        _apply_house_font(heading)
        heading.font.size = Pt(geometry.size_pt)
        heading.font.bold = True
        heading.font.italic = False
        _apply_house_text_color(heading)
        set_style_spacing(heading.paragraph_format, geometry.spacing)
        heading.paragraph_format.keep_with_next = True


def _apply_house_font(style: ParagraphStyle) -> None:
    """The house font on all four script slots, with every theme-font attribute removed."""
    style.font.name = HOUSE_FONT_FAMILIES[0]
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        rFonts.set(qn(f"w:{attribute}"), HOUSE_FONT_FAMILIES[0])
    for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rFonts.attrib.pop(qn(f"w:{attribute}"), None)


def _apply_house_text_color(style: ParagraphStyle) -> None:
    """The template's text colour, with the theme colour attributes removed."""
    style.font.color.rgb = RGBColor.from_string(TEXT_COLOR_HEX)
    color = style.element.get_or_add_rPr().find(qn("w:color"))
    if color is not None:
        for attribute in ("themeColor", "themeShade", "themeTint"):
            color.attrib.pop(qn(f"w:{attribute}"), None)


def set_style_spacing(paragraph_format: ParagraphFormat, spacing: BlockSpacing) -> None:
    paragraph_format.space_before = Mm(spacing.space_before_mm)
    paragraph_format.space_after = Mm(spacing.space_after_mm)
