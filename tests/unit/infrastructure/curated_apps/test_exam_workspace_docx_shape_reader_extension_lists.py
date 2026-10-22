"""Shape reader: ignorable ``a:extLst`` extension lists (TASK-SKRIPT-39-04-22 unit 1)."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_reader import (  # noqa: E501
    read_shape_figure,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_reader_test_support import (
    BLACK_LINE,
    canvas_xml,
    group_xml,
    label_xml,
    make_document,
    make_drawing,
    para_xml,
    read_one,
    style_xml,
    theme_xml,
    wsp_xml,
)

pytestmark = pytest.mark.unit


# --- extension lists ---------------------------------------------------------------------------

# Word writes the VML fallback's fill and line into a:extLst; nothing draws them, so the reader
# ignores the list. The hidden colours differ from the visible ones so a leak would show.
_EXT_LST = (
    '<a:extLst><a:ext uri="{909E8E84-426E-40DD-AFC4-6F175D3DCCD1}"><a14:hiddenFill>'
    '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a14:hiddenFill></a:ext>'
    '<a:ext uri="{91240B29-F687-4F45-9708-019B960494DF}"><a14:hiddenLine w="38100">'
    '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></a14:hiddenLine></a:ext></a:extLst>'
)


def test_an_extension_list_in_the_shape_properties_is_ignored() -> None:
    assert read_one(wsp_xml(sp_extra=_EXT_LST)) == read_one(wsp_xml())


def test_an_extension_list_in_the_outline_is_ignored() -> None:
    line = BLACK_LINE.replace("</a:ln>", f"{_EXT_LST}</a:ln>")

    assert read_one(wsp_xml(line=line)) == read_one(wsp_xml())


def test_an_extension_list_in_a_theme_line_style_is_ignored() -> None:
    plain = theme_xml()
    extended = plain.replace(b"</a:ln>", _EXT_LST.encode() + b"</a:ln>", 1).replace(
        b"<a:theme ", b'<a:theme xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" '
    )
    assert extended != plain
    shape = wsp_xml(line="", style=style_xml(ln=1, fill=0))

    assert read_one(shape, document=make_document(extended)) == read_one(
        shape, document=make_document(plain)
    )


def test_an_extension_list_in_the_group_properties_is_ignored() -> None:
    plain = group_xml(wsp_xml())
    extended = plain.replace("</a:xfrm></wpg:grpSpPr>", f"</a:xfrm>{_EXT_LST}</wpg:grpSpPr>")
    assert extended != plain

    assert read_shape_figure(
        make_drawing(extended, uri="wpg"), make_document()
    ) == read_shape_figure(make_drawing(plain, uri="wpg"), make_document())


def test_an_extension_list_in_the_body_properties_is_ignored() -> None:
    plain = wsp_xml(**label_xml(para_xml("t"), body="<wps:bodyPr/>"))
    extended = wsp_xml(**label_xml(para_xml("t"), body=f"<wps:bodyPr>{_EXT_LST}</wps:bodyPr>"))

    assert read_one(extended) == read_one(plain)


def test_an_extension_list_in_the_canvas_layers_is_ignored() -> None:
    plain = canvas_xml(wsp_xml())
    extended = plain.replace(
        "<a:ln><a:noFill/></a:ln>", f"<a:ln><a:noFill/>{_EXT_LST}</a:ln>{_EXT_LST}"
    ).replace("<wpc:bg><a:noFill/></wpc:bg>", f"<wpc:bg><a:noFill/>{_EXT_LST}</wpc:bg>")
    assert extended.count("a:extLst>") == 6

    assert read_shape_figure(
        make_drawing(extended, uri="wpc"), make_document()
    ) == read_shape_figure(make_drawing(plain, uri="wpc"), make_document())
