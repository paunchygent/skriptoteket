"""Self-contained shape markup of a Word drawing: kept whole or refused (D8, D12)."""

from pathlib import Path

import pytest
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from lxml import etree  # type: ignore[import-untyped]

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    ShapeFigure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_markup import (  # noqa: E501
    self_contained_shapes,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_reader import (  # noqa: E501
    read_shape_figure,
)

_FIXTURE = Path("tests/fixtures/exam_conversion/pdf_corpus/metodprov_med_bilder.docx")
_WPG = "{http://schemas.microsoft.com/office/word/2010/wordprocessingGroup}wgp"
_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
)


def _fixture_drawings() -> list[tuple[BaseOxmlElement, ShapeFigure]]:
    document = Document(str(_FIXTURE))
    body = document.element.body
    drawings = [
        drawing
        for child in body
        for drawing in child.iter(qn("w:drawing"))
        if next(drawing.iter(_WPG), None) is not None
    ]
    assert len(drawings) == 2
    return [(drawing, read_shape_figure(drawing, document)) for drawing in drawings]


def _drawing(inner: str) -> BaseOxmlElement:
    return parse_xml(f"<w:drawing {_NS}>{inner}</w:drawing>")


_NO_FIGURE = ShapeFigure(width_emu=1, height_emu=1, shapes=())


def _canonical(element: BaseOxmlElement) -> bytes:
    canonical: bytes = etree.tostring(element, method="c14n", exclusive=True)
    return canonical


def test_fixture_drawings_come_back_as_standalone_group_markup() -> None:
    first, second = _fixture_drawings()

    markups = [self_contained_shapes(*first), self_contained_shapes(*second)]

    for markup, labels in zip(
        markups,
        (
            ("Svenska gymnasieelever (populationen)", "Elever på ett program (urvalet)"),
            ("Alla elever på skolan", "Elever som är i biblioteket", "Svarar på frågan"),
        ),
        strict=True,
    ):
        assert markup is not None
        root = etree.fromstring(
            markup.encode(), etree.XMLParser(resolve_entities=False, no_network=True)
        )
        assert root.tag == qn("w:drawing")
        assert next(root.iter(_WPG), None) is not None
        for label in labels:
            assert label in markup
        assert "AlternateContent" not in markup
        assert "urn:schemas-microsoft-com:vml" not in markup


def test_returned_markup_keeps_the_subtree_apart_from_what_it_states_itself() -> None:
    for drawing, figure in _fixture_drawings():
        before = _canonical(drawing)

        markup = self_contained_shapes(drawing, figure)

        assert markup is not None
        reparsed = etree.fromstring(
            markup.encode(), etree.XMLParser(resolve_entities=False, no_network=True)
        )
        assert [e.get("id") for e in reparsed.iter(qn("wp:docPr"))] == [
            e.get("id") for e in drawing.iter(qn("wp:docPr"))
        ]
        assert [e.get("prst") for e in reparsed.iter("{*}prstGeom")] == [
            e.get("prst") for e in drawing.iter("{*}prstGeom")
        ]
        assert [t.text for t in reparsed.iter(qn("w:t"))] == [
            t.text for t in drawing.iter(qn("w:t"))
        ]
        assert next(reparsed.iter("{*}schemeClr"), None) is None
        assert next(reparsed.iter("{*}style"), None) is None
        assert _canonical(drawing) == before


def test_source_tree_is_left_untouched_by_the_serialization() -> None:
    drawing, figure = _fixture_drawings()[0]
    parent = drawing.getparent()
    before = _canonical(drawing)

    self_contained_shapes(drawing, figure)

    assert drawing.getparent() is parent
    assert _canonical(drawing) == before


def test_shapes_that_do_not_pair_with_the_figure_are_not_stored() -> None:
    drawing, figure = _fixture_drawings()[0]

    assert (
        self_contained_shapes(drawing, ShapeFigure(figure.width_emu, figure.height_emu, ())) is None
    )


def test_picture_embed_makes_the_drawing_not_self_contained() -> None:
    drawing = _drawing('<a:blip r:embed="rId5"/>')

    assert self_contained_shapes(drawing, _NO_FIGURE) is None


def test_hyperlink_relationship_makes_the_drawing_not_self_contained() -> None:
    drawing = _drawing('<a:hlinkClick r:id="rId7"/>')

    assert self_contained_shapes(drawing, _NO_FIGURE) is None


@pytest.mark.parametrize(
    "inner",
    [
        '<w:r><w:footnoteReference w:id="1"/></w:r>',
        '<w:r><w:endnoteReference w:id="1"/></w:r>',
        '<w:r><w:commentReference w:id="1"/></w:r>',
        "<w:r><w:object/></w:r>",
        "<w:r><w:pict/></w:r>",
    ],
)
def test_references_to_other_parts_make_the_drawing_not_self_contained(inner: str) -> None:
    drawing = _drawing(f"<w:txbxContent><w:p>{inner}</w:p></w:txbxContent>")

    assert self_contained_shapes(drawing, _NO_FIGURE) is None


def test_a_drawing_without_shapes_is_returned_whole() -> None:
    drawing = _drawing("<w:txbxContent><w:p><w:r><w:t>Hej</w:t></w:r></w:p></w:txbxContent>")

    markup = self_contained_shapes(drawing, _NO_FIGURE)

    assert markup is not None
    assert "Hej" in markup
