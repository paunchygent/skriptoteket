"""Shape reader: fills, outlines, colours and the theme (TASK-SKRIPT-39-04-22 unit 1)."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    Arrowhead,
    ArrowheadKind,
    ShapeOutline,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_reader_test_support import (
    make_document,
    read_one,
    rejected_shape,
    scheme_fill,
    style_xml,
    theme_xml,
    wsp_xml,
)

pytestmark = pytest.mark.unit


# --- fill and outline ------------------------------------------------------------------------


def test_no_fill_element_and_no_style_means_no_fill() -> None:
    shape = read_one(wsp_xml(fill=""))

    assert shape.fill is None


def test_solid_fill_colour_is_upper_case_hex() -> None:
    shape = read_one(wsp_xml(fill='<a:solidFill><a:srgbClr val="ddebf7"/></a:solidFill>'))

    assert shape.fill == "DDEBF7"


def test_outline_defaults_to_9525_and_reads_dash_and_arrowheads() -> None:
    line = (
        '<a:ln><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill><a:prstDash val="sysDash"/>'
        '<a:round/><a:headEnd type="oval"/><a:tailEnd type="triangle" w="lg" len="sm"/></a:ln>'
    )

    shape = read_one(wsp_xml(line=line, prst="straightConnector1", connector=True))

    assert shape.outline == ShapeOutline(
        color="FF0000",
        width_emu=9525,
        dash="sysDash",
        head=Arrowhead("oval"),
        tail=Arrowhead("triangle", width="lg", length="sm"),
    )


@pytest.mark.parametrize("kind", ["triangle", "arrow", "stealth", "oval", "diamond"])
def test_each_arrowhead_kind_is_read(kind: ArrowheadKind) -> None:
    line = (
        '<a:ln w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
        f'<a:tailEnd type="{kind}"/></a:ln>'
    )

    shape = read_one(wsp_xml(line=line))

    assert shape.outline is not None
    assert shape.outline.tail == Arrowhead(kind)


def test_arrowhead_type_none_is_no_arrowhead() -> None:
    line = (
        '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
        '<a:headEnd type="none"/><a:tailEnd/></a:ln>'
    )

    shape = read_one(wsp_xml(line=line))

    assert shape.outline is not None
    assert (shape.outline.head, shape.outline.tail) == (None, None)


def test_no_fill_outline_is_no_outline() -> None:
    assert read_one(wsp_xml(line="<a:ln><a:noFill/></a:ln>")).outline is None


def test_no_outline_element_and_no_style_is_no_outline() -> None:
    assert read_one(wsp_xml(line="")).outline is None


# --- colours and the theme -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("inner", "expected"),
    [
        ("", "4472C4"),
        ('<a:lumMod val="60000"/><a:lumOff val="40000"/>', "8FAADC"),
        ('<a:lumMod val="40000"/><a:lumOff val="60000"/>', "B4C7E7"),
        ('<a:lumMod val="75000"/>', "2F5597"),
        ('<a:shade val="50000"/>', "2F528F"),
        ('<a:alpha val="100000"/>', "4472C4"),
    ],
)
def test_scheme_colour_resolves_through_the_theme_with_modifiers(inner: str, expected: str) -> None:
    shape = read_one(wsp_xml(fill=scheme_fill(inner)), document=make_document(theme_xml()))

    assert shape.fill == expected


def test_tint_lightens_towards_white_and_full_tint_is_the_colour() -> None:
    document = make_document(theme_xml())

    full = read_one(wsp_xml(fill=scheme_fill('<a:tint val="100000"/>')), document=document)
    none = read_one(wsp_xml(fill=scheme_fill('<a:tint val="0"/>')), document=document)

    assert full.fill == "4472C4"
    assert none.fill == "FFFFFF"


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("tx1", "000000"),
        ("bg1", "FFFFFF"),
        ("tx2", "44546A"),
        ("bg2", "E7E6E6"),
        ("accent2", "ED7D31"),
    ],
)
def test_scheme_names_map_to_the_theme_slots(scheme: str, expected: str) -> None:
    shape = read_one(wsp_xml(fill=scheme_fill("", scheme)), document=make_document(theme_xml()))

    assert shape.fill == expected


def test_sys_and_preset_colours() -> None:
    sys_fill = '<a:solidFill><a:sysClr val="windowText" lastClr="1A2B3C"/></a:solidFill>'
    white = '<a:solidFill><a:prstClr val="white"/></a:solidFill>'
    black = '<a:solidFill><a:prstClr val="black"/></a:solidFill>'

    assert read_one(wsp_xml(fill=sys_fill)).fill == "1A2B3C"
    assert read_one(wsp_xml(fill=white)).fill == "FFFFFF"
    assert read_one(wsp_xml(fill=black)).fill == "000000"


def test_a_concrete_colour_never_reads_the_theme() -> None:
    shape = read_one(
        wsp_xml(fill='<a:solidFill><a:srgbClr val="010203"/></a:solidFill>'),
        document=make_document(drop_theme=True),
    )

    assert shape.fill == "010203"


def test_style_fill_and_line_references_resolve_through_the_theme() -> None:
    shape = read_one(
        wsp_xml(fill="", line="", style=style_xml()), document=make_document(theme_xml())
    )

    assert shape.fill == "4472C4"
    assert shape.outline == ShapeOutline(color="2F528F", width_emu=12700)


def test_style_index_zero_means_no_fill_and_no_outline() -> None:
    shape = read_one(
        wsp_xml(fill="", line="", style=style_xml(ln=0, fill=0)),
        document=make_document(theme_xml()),
    )

    assert (shape.fill, shape.outline) == (None, None)


def test_a_shape_that_sets_its_own_fill_ignores_the_style_fill() -> None:
    shape = read_one(
        wsp_xml(fill='<a:solidFill><a:srgbClr val="00FF00"/></a:solidFill>', style=style_xml()),
        document=make_document(theme_xml()),
    )

    assert shape.fill == "00FF00"


def test_style_line_takes_the_theme_width_unless_the_shape_sets_one() -> None:
    explicit = '<a:ln w="3175"/>'
    shape = read_one(
        wsp_xml(fill="", line=explicit, style=style_xml()), document=make_document(theme_xml())
    )

    assert shape.outline == ShapeOutline(color="2F528F", width_emu=3175)


def test_style_fill_may_be_a_concrete_theme_colour() -> None:
    shape = read_one(
        wsp_xml(fill="", line="", style=style_xml(ln=0, fill=3)),
        document=make_document(theme_xml()),
    )

    assert shape.fill == "123456"


def test_a_style_without_a_theme_is_unsupported() -> None:
    rejected_shape(wsp_xml(fill="", style=style_xml()), "theme", make_document(drop_theme=True))


def test_a_scheme_colour_without_a_theme_is_unsupported() -> None:
    rejected_shape(wsp_xml(fill=scheme_fill("")), "theme", make_document(drop_theme=True))


def test_style_effect_reference_to_an_empty_effect_list_is_fine() -> None:
    shape = read_one(
        wsp_xml(style=style_xml(ln=0, fill=0, effect=2)), document=make_document(theme_xml())
    )

    assert shape.fill is None
