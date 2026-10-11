from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.styles.style import CharacterStyle, ParagraphStyle

from .profiles import PROFILE_PRINT_BW, PROFILE_PRINT_COLOR

# =========================
# DOCX reference doc (simple, non-brittle)
# =========================


def _ensure_style(doc: DocxDocument, name: str, style_type: WD_STYLE_TYPE) -> None:
    """Create the style in the reference doc unless it already exists."""
    if name not in doc.styles:
        doc.styles.add_style(name, style_type)


def _set_style_font(
    doc: DocxDocument,
    style_name: str,
    *,
    font_name: str | None = None,
    size_pt: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
    underline: bool | None = None,
) -> None:
    style: CharacterStyle = doc.styles[style_name]
    font = style.font
    if font_name is not None:
        font.name = font_name
        font.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    if size_pt is not None:
        font.size = Pt(size_pt)
    if bold is not None:
        font.bold = bold
    if color is not None:
        font.color.rgb = color
    if underline is not None:
        font.underline = underline


def _set_style_paragraph(
    doc: DocxDocument,
    style_name: str,
    *,
    space_before_pt: float | None = None,
    space_after_pt: float | None = None,
    line_spacing: float | None = None,
) -> None:
    style: ParagraphStyle = doc.styles[style_name]
    fmt = style.paragraph_format
    if space_before_pt is not None:
        fmt.space_before = Pt(space_before_pt)
    if space_after_pt is not None:
        fmt.space_after = Pt(space_after_pt)
    if line_spacing is not None:
        fmt.line_spacing = line_spacing


def _apply_docx_profile_styles(doc: DocxDocument, profile: str) -> None:
    # Margins
    section = doc.sections[0]
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    navy = RGBColor(0x08, 0x2B, 0x4C)  # HuleEdu deep navy
    action = RGBColor(0x3F, 0x7F, 0x78)  # HuleEdu Verdigris action
    black = RGBColor(0, 0, 0)

    if profile == PROFILE_PRINT_BW:
        body_font = "Liberation Serif"
        heading_font = "Liberation Serif"
        code_font = "Liberation Mono"
        body_size = 12
        h1_size, h2_size, h3_size = 20, 14, 12
        heading_color = black
        link_color = black
        body_line_spacing = 1.1
        heading_space_before = (14, 12, 10)
        heading_space_after = (6, 6, 4)
    elif profile == PROFILE_PRINT_COLOR:
        body_font = "Noto Sans"
        heading_font = "Noto Sans"
        code_font = "Liberation Mono"
        body_size = 11
        h1_size, h2_size, h3_size = 22, 16, 13
        heading_color = navy
        link_color = action
        body_line_spacing = 1.2
        heading_space_before = (18, 14, 12)
        heading_space_after = (8, 6, 4)
    else:
        body_font = "Noto Serif"
        heading_font = "Noto Sans"
        code_font = "Liberation Mono"
        body_size = 11
        h1_size, h2_size, h3_size = 21, 15, 13
        heading_color = navy
        link_color = navy
        body_line_spacing = 1.15
        heading_space_before = (16, 12, 10)
        heading_space_after = (6, 5, 4)

    code_size = 10.5 if body_size <= 11 else 11

    # Common paragraph styles
    _set_style_font(doc, "Normal", font_name=body_font, size_pt=body_size, bold=False, color=black)
    _set_style_font(
        doc, "Heading 1", font_name=heading_font, size_pt=h1_size, bold=True, color=heading_color
    )
    _set_style_font(
        doc, "Heading 2", font_name=heading_font, size_pt=h2_size, bold=True, color=heading_color
    )
    _set_style_font(
        doc, "Heading 3", font_name=heading_font, size_pt=h3_size, bold=True, color=heading_color
    )

    for s in ("List Paragraph", "List Bullet", "List Number"):
        _set_style_font(doc, s, font_name=body_font, size_pt=body_size, bold=False, color=black)

    # Paragraph spacing + line height
    _set_style_paragraph(
        doc, "Normal", space_before_pt=0, space_after_pt=6, line_spacing=body_line_spacing
    )
    _set_style_paragraph(
        doc,
        "Heading 1",
        space_before_pt=heading_space_before[0],
        space_after_pt=heading_space_after[0],
        line_spacing=1.1,
    )
    _set_style_paragraph(
        doc,
        "Heading 2",
        space_before_pt=heading_space_before[1],
        space_after_pt=heading_space_after[1],
        line_spacing=1.1,
    )
    _set_style_paragraph(
        doc,
        "Heading 3",
        space_before_pt=heading_space_before[2],
        space_after_pt=heading_space_after[2],
        line_spacing=1.1,
    )
    for s in ("List Paragraph", "List Bullet", "List Number"):
        _set_style_paragraph(
            doc, s, space_before_pt=0, space_after_pt=4, line_spacing=body_line_spacing
        )

    # Hyperlinks
    if profile == PROFILE_PRINT_BW:
        _set_style_font(doc, "Hyperlink", color=black, underline=True)
        _set_style_font(doc, "FollowedHyperlink", color=black, underline=True)
    else:
        _set_style_font(doc, "Hyperlink", color=link_color, underline=True)
        _set_style_font(doc, "FollowedHyperlink", color=link_color, underline=True)

    # Code-related styles Pandoc commonly uses in DOCX
    for s in ("Verbatim Char", "Source Code", "Code"):
        _set_style_font(doc, s, font_name=code_font, size_pt=code_size, color=black)
    _set_style_paragraph(doc, "Source Code", space_before_pt=6, space_after_pt=6, line_spacing=1.0)


def make_reference_docx(profile: str, tmpdir: Path) -> Path:
    """
    Reference doc produced by python-docx only (no extra pandoc subprocess step).
    We explicitly ensure key styles exist, so Pandoc has something to map to.
    """
    ref_path = tmpdir / f"reference_{profile}.docx"
    doc: DocxDocument = Document()

    # Ensure styles that matter for "no color" exist
    _ensure_style(doc, "Hyperlink", WD_STYLE_TYPE.CHARACTER)
    _ensure_style(doc, "FollowedHyperlink", WD_STYLE_TYPE.CHARACTER)
    _ensure_style(doc, "Verbatim Char", WD_STYLE_TYPE.CHARACTER)
    _ensure_style(doc, "Code", WD_STYLE_TYPE.CHARACTER)
    _ensure_style(doc, "Source Code", WD_STYLE_TYPE.PARAGRAPH)

    _apply_docx_profile_styles(doc, profile)
    doc.add_paragraph("Reference document for Pandoc DOCX styling (generated).")
    doc.save(str(ref_path))
    return ref_path
