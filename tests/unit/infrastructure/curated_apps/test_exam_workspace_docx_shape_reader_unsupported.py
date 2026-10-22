"""Shape reader rejections: one unsupported case per D2 rule family (TASK-SKRIPT-39-04-22 unit 1).

The reader must raise ``UnsupportedShapeFigure`` naming what it does not model and never
return a partial figure.
"""

from __future__ import annotations

import pytest
from docx.oxml import parse_xml

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_reader import (  # noqa: E501
    read_shape_figure,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_reader_test_support import (
    NS,
    canvas_xml,
    group_xml,
    label_xml,
    make_document,
    make_drawing,
    para_xml,
    read_one,
    rejected,
    rejected_shape,
    scheme_fill,
    shape_text,
    style_xml,
    theme_xml,
    wsp_xml,
)

pytestmark = pytest.mark.unit


# --- unsupported: one case per rule family ---------------------------------------------------


def test_custom_geometry_is_unsupported() -> None:
    rejected_shape(wsp_xml(geometry="<a:custGeom><a:pathLst/></a:custGeom>"), "custGeom")


def test_an_unlisted_preset_is_unsupported() -> None:
    rejected_shape(wsp_xml(prst="star5"), "star5")


def test_a_guide_formula_other_than_val_is_unsupported() -> None:
    rejected_shape(wsp_xml(guides='<a:gd name="adj" fmla="*/ w 1 2"/>'), "fmla")


@pytest.mark.parametrize(
    ("fill", "needle"),
    [
        ("<a:gradFill><a:gsLst/></a:gradFill>", "gradFill"),
        ('<a:blipFill><a:blip r:embed="rId9"/></a:blipFill>', "blipFill"),
        ('<a:pattFill prst="pct5"/>', "pattFill"),
        ("<a:grpFill/>", "grpFill"),
    ],
)
def test_non_solid_fills_are_unsupported(fill: str, needle: str) -> None:
    rejected_shape(wsp_xml(fill=fill), needle)


def test_a_gradient_outline_is_unsupported() -> None:
    rejected_shape(wsp_xml(line="<a:ln><a:gradFill><a:gsLst/></a:gradFill></a:ln>"), "gradFill")


def test_a_custom_dash_is_unsupported() -> None:
    line = (
        '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
        '<a:custDash><a:ds d="1" sp="1"/></a:custDash></a:ln>'
    )
    rejected_shape(wsp_xml(line=line), "custDash")


def test_an_unknown_dash_is_unsupported() -> None:
    line = (
        '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:prstDash val="zig"/></a:ln>'
    )
    rejected_shape(wsp_xml(line=line), "zig")


def test_an_unknown_arrowhead_type_is_unsupported() -> None:
    line = (
        '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
        '<a:tailEnd type="swoosh"/></a:ln>'
    )
    rejected_shape(wsp_xml(line=line), "swoosh")


@pytest.mark.parametrize(
    "extra",
    [
        '<a:effectLst><a:outerShdw blurRad="1"/></a:effectLst>',
        "<a:effectDag><a:cont/></a:effectDag>",
        '<a:scene3d><a:camera prst="orthographicFront"/></a:scene3d>',
        '<a:sp3d extrusionH="100"/>',
    ],
)
def test_spPr_effects_are_unsupported(extra: str) -> None:
    rejected_shape(wsp_xml(sp_extra=extra), "effect" if "ffect" in extra else "3d")


def test_an_empty_effect_list_is_no_effect() -> None:
    assert read_one(wsp_xml(sp_extra="<a:effectLst/>")).preset == "rect"


def test_a_style_effect_reference_to_a_shadow_is_unsupported() -> None:
    theme = theme_xml(effect_third='<a:effectLst><a:outerShdw blurRad="40000"/></a:effectLst>')

    rejected_shape(wsp_xml(style=style_xml(ln=0, fill=0, effect=3)), "effect", make_document(theme))


def test_a_gradient_theme_fill_is_unsupported() -> None:
    rejected_shape(
        wsp_xml(fill="", style=style_xml(fill=2)), "gradFill", make_document(theme_xml())
    )


def test_a_non_solid_theme_line_is_unsupported() -> None:
    rejected_shape(wsp_xml(line="", style=style_xml(ln=3)), "gradFill", make_document(theme_xml()))


def test_alpha_below_full_is_unsupported() -> None:
    fill = '<a:solidFill><a:srgbClr val="000000"><a:alpha val="50000"/></a:srgbClr></a:solidFill>'
    rejected_shape(wsp_xml(fill=fill), "alpha")


def test_a_colour_modifier_outside_the_list_is_unsupported() -> None:
    fill = '<a:solidFill><a:srgbClr val="808080"><a:satMod val="50000"/></a:srgbClr></a:solidFill>'
    rejected_shape(wsp_xml(fill=fill), "satMod")


def test_a_preset_colour_other_than_black_and_white_is_unsupported() -> None:
    rejected_shape(wsp_xml(fill='<a:solidFill><a:prstClr val="red"/></a:solidFill>'), "red")


def test_a_linked_text_box_is_unsupported() -> None:
    rejected_shape(
        wsp_xml(sp_extra="").replace("</wps:wsp>", "<wps:linkedTxbx id='1' seq='0'/></wps:wsp>"),
        "linkedTxbx",
    )


def test_a_picture_inside_a_group_is_unsupported() -> None:
    picture = '<pic:pic><pic:blipFill><a:blip r:embed="rId9"/></pic:blipFill></pic:pic>'
    group = group_xml(wsp_xml() + picture)

    rejected(make_drawing(group, uri="wpg"), "pic")


def test_a_graphic_frame_inside_a_canvas_is_unsupported() -> None:
    rejected(make_drawing(canvas_xml("<wpg:graphicFrame/>"), uri="wpc"), "graphicFrame")


@pytest.mark.parametrize(
    "uri", ["http://schemas.openxmlformats.org/drawingml/2006/chart",
            "http://schemas.openxmlformats.org/drawingml/2006/diagram",
            "http://schemas.openxmlformats.org/drawingml/2006/picture"],
)  # fmt: skip
def test_a_graphic_that_is_not_a_shape_container_is_unsupported(uri: str) -> None:
    rejected(make_drawing("<a:ext/>", uri=uri), uri.rsplit("/", 1)[1])


def test_a_group_with_zero_child_extent_is_unsupported() -> None:
    rejected(make_drawing(group_xml(wsp_xml(), ch_ext=(0, 500)), uri="wpg"), "chExt")


def test_a_shape_turned_off_the_axes_in_an_unevenly_scaled_group_is_unsupported() -> None:
    group = group_xml(wsp_xml(xfrm_attrs='rot="2700000"'), ext=(2000, 500), ch_ext=(1000, 500))

    rejected(make_drawing(group, uri="wpg", cx=2000, cy=500), "scaled")


def test_a_canvas_background_with_a_fill_is_unsupported() -> None:
    canvas = canvas_xml(
        wsp_xml(),
        background='<wpc:bg><a:solidFill><a:srgbClr val="FFFF00"/></a:solidFill></wpc:bg>',
    )

    rejected(make_drawing(canvas, uri="wpc"), "bg")


def test_a_canvas_whole_with_an_outline_is_unsupported() -> None:
    canvas = canvas_xml(wsp_xml()).replace(
        "<a:ln><a:noFill/></a:ln>",
        '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln>',
    )

    rejected(make_drawing(canvas, uri="wpc"), "whole")


def test_a_canvas_without_background_elements_is_fine() -> None:
    canvas = f"<wpc:wpc>{wsp_xml()}</wpc:wpc>"

    assert len(read_shape_figure(make_drawing(canvas, uri="wpc"), make_document()).shapes) == 1


def test_a_hyperlink_in_a_label_is_unsupported() -> None:
    content = '<w:p><w:hyperlink w:anchor="x"><w:r><w:t>l</w:t></w:r></w:hyperlink></w:p>'
    rejected_shape(wsp_xml(**label_xml(content)), "hyperlink")


def test_a_table_in_a_label_is_unsupported() -> None:
    rejected_shape(wsp_xml(**label_xml("<w:tbl/>")), "tbl")


@pytest.mark.parametrize(
    ("run_child", "name"),
    [
        ('<w:fldChar w:fldCharType="begin"/>', "w:fldChar"),
        ("<w:instrText>PAGE</w:instrText>", "w:instrText"),
        ("<w:drawing/>", "w:drawing"),
        ("<w:pict/>", "w:pict"),
        ("<w:object/>", "w:object"),
        ('<w:footnoteReference w:id="1"/>', "w:footnoteReference"),
        ('<w:endnoteReference w:id="1"/>', "w:endnoteReference"),
        ('<w:commentReference w:id="1"/>', "w:commentReference"),
    ],
)
def test_a_run_with_a_field_object_or_reference_is_unsupported(run_child: str, name: str) -> None:
    content = f"<w:p><w:r><w:t>a</w:t>{run_child}</w:r></w:p>"
    rejected_shape(wsp_xml(**label_xml(content)), name)


def test_a_numbered_label_paragraph_is_unsupported() -> None:
    ppr = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="3"/></w:numPr>'
    rejected_shape(wsp_xml(**label_xml(para_xml("a", ppr=ppr))), "numPr")


@pytest.mark.parametrize("anchor", ["just", "dist"])
def test_an_anchor_other_than_top_centre_bottom_is_unsupported(anchor: str) -> None:
    rejected_shape(
        wsp_xml(**label_xml(para_xml("t"), body=f'<wps:bodyPr anchor="{anchor}"/>')), anchor
    )


@pytest.mark.parametrize("attrs", ['vert="vert"', 'rot="5400000"'])
def test_vertical_or_rotated_text_is_unsupported(attrs: str) -> None:
    rejected_shape(wsp_xml(**label_xml(para_xml("t"), body=f"<wps:bodyPr {attrs}/>")), "bodyPr")


def test_a_group_without_shapes_is_unsupported() -> None:
    rejected(make_drawing(group_xml(""), uri="wpg"), "no shapes")


def test_a_drawing_without_a_container_is_unsupported() -> None:
    rejected(parse_xml(f"<w:drawing {NS}/>"), "wp:inline")


def test_a_drawing_with_an_empty_or_negative_extent_is_unsupported() -> None:
    rejected(make_drawing(wsp_xml(), cx=0, cy=0), "extent")
    rejected(make_drawing(wsp_xml(), cx=-5), "extent")


def test_a_plain_horizontal_line_has_a_zero_height_box_and_is_plain_lines() -> None:
    line = wsp_xml(prst="line", ext=(4000, 0), connector=True)

    figure = read_shape_figure(make_drawing(line, cx=4000, cy=0), make_document())

    assert (figure.width_emu, figure.height_emu) == (4000, 0)
    assert figure.plain_lines


def test_a_shape_without_geometry_is_unsupported() -> None:
    rejected_shape(wsp_xml(geometry=" "), "geometry")


def test_two_wsp_in_a_single_shape_graphic_is_unsupported() -> None:
    rejected(make_drawing(wsp_xml() + wsp_xml()), "one")


def test_the_theme_is_parsed_without_resolving_entities() -> None:
    hostile = (
        b'<?xml version="1.0"?><!DOCTYPE t [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        b'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<a:themeElements><a:clrScheme><a:accent1><a:srgbClr val="&x;"/></a:accent1>'
        b"</a:clrScheme></a:themeElements></a:theme>"
    )

    rejected_shape(wsp_xml(fill=scheme_fill("")), "theme", make_document(hostile))


@pytest.mark.parametrize("mark", ["strike", "highlight", "vanish", "vertAlign"])
def test_a_run_mark_the_label_model_lacks_is_unsupported(mark: str) -> None:
    val = {"highlight": ' w:val="yellow"', "vertAlign": ' w:val="superscript"'}.get(mark, "")
    rejected_shape(
        wsp_xml(**label_xml(para_xml("t", rpr=f"<w:{mark}{val}/>"))),
        f"w:{mark}",
    )


def test_a_mark_switched_off_is_not_a_mark() -> None:
    rpr = '<w:strike w:val="0"/><w:vertAlign w:val="baseline"/><w:highlight w:val="none"/>'

    assert shape_text(read_one(wsp_xml(**label_xml(para_xml("t", rpr=rpr))))) == "t"


def test_word_saved_text_box_markup_is_read() -> None:
    """Word writes a text warp of "none" into bodyPr and the resolved hex beside a theme colour."""
    body = (
        '<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="91440" tIns="45720" rIns="91440" '
        'bIns="45720" anchor="ctr" anchorCtr="0"><a:prstTxWarp prst="textNoShape"><a:avLst/>'
        "</a:prstTxWarp><a:noAutofit/></wps:bodyPr>"
    )
    rpr = '<w:color w:val="FFFFFF" w:themeColor="background1"/>'

    shape = read_one(wsp_xml(**label_xml(para_xml("t", rpr=rpr), body=body)))

    assert shape.label is not None
    assert (shape.label.paragraphs[0].runs[0].color, shape.label.anchor) == ("FFFFFF", "ctr")


def test_a_shrinking_text_fit_is_unsupported() -> None:
    body = '<wps:bodyPr><a:normAutofit fontScale="92500" lnSpcReduction="10000"/></wps:bodyPr>'

    rejected_shape(wsp_xml(**label_xml(para_xml("t"), body=body)), "normAutofit")
