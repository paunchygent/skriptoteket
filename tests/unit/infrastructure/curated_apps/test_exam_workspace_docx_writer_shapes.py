"""Stored Word shapes in the exam workspace DOCX writer (TASK-SKRIPT-39-04-22 D9).

A picture whose asset stores the Word shapes it was drawn from prints those shapes as an
editable inline drawing in its question paragraph. These tests export documents with stored
shapes, re-open the produced bytes and inspect ``word/document.xml``: the inline drawing and
its ids, unusable markup falling back to the picture, connectors that keep their shapes, and
wide drawings fitted to the text width.
"""

import copy
import io
import zipfile
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from docx.shared import Mm
from lxml import etree

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    TEXT_WIDTH_MM,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    png,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

_SHAPES_FIXTURE = Path("tests/fixtures/exam_conversion/pdf_corpus/metodprov_med_bilder.docx")
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NAMESPACES = {
    "w": _W,
    "mc": _MC,
    "wp": _WP,
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
}
_ASSET_A = "asset_" + "a" * 16
_ASSET_B = "asset_" + "b" * 16
_ASSET_C = "asset_" + "c" * 16
_LABELS = ("Svenska gymnasieelever (populationen)", "Elever på ett program (urvalet)")


def _stored_group_shapes() -> str:
    """The fixture's drawn group (two labelled ellipses) as the import stores it."""
    with zipfile.ZipFile(_SHAPES_FIXTURE) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    drawings = root.xpath("//mc:Choice/w:drawing", namespaces=_NAMESPACES)
    assert drawings, "the fixture holds a drawn group in mc:Choice"
    return str(etree.tostring(copy.deepcopy(drawings[0]), encoding="unicode"))


def _edited_shapes(edit: Callable[[etree._Element], None]) -> str:
    drawing = etree.fromstring(_stored_group_shapes())
    edit(drawing)
    return str(etree.tostring(drawing, encoding="unicode"))


def _picture_document(
    *pictures: tuple[str, str | None],
) -> tuple[NativeExamDocument, dict[str, bytes]]:
    """One free-text question per (asset id, stored shapes), each with a picture in its body."""
    payloads = {asset_id: png((20, 90, 20, 255), (40, 20)) for asset_id, _ in pictures}
    items = []
    for sequence, (asset_id, _) in enumerate(pictures, start=1):
        item = make_free_text_item(sequence=sequence, item_id=f"item_{sequence:03d}")
        items.append(
            item.model_copy(
                update={
                    "body": (
                        NativeParagraph(
                            heading_level=None,
                            segments=(
                                NativeTextSegment(text=f"Se bild {sequence}", marks=()),
                                NativeAssetSegment(asset_id=asset_id),
                            ),
                        ),
                    )
                }
            )
        )
    assets = tuple(
        NativeExamAsset(
            asset_id=asset_id,
            sha256="0" * 64,
            media_type="image/png",
            byte_length=len(payloads[asset_id]),
            docx_shapes=shapes,
        )
        for asset_id, shapes in pictures
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Bildprov",
        items=tuple(items),
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, payloads


def _export(*pictures: tuple[str, str | None]) -> tuple[bytes, etree._Element]:
    """Export, re-open and validate the file; return its bytes and its document.xml root."""
    document, payloads = _picture_document(*pictures)
    writer = ExamWorkspaceDocxWriter()
    content = writer.build_docx_bytes(document, assets_by_id=payloads)
    Document(io.BytesIO(content))
    writer.validate_docx_bytes(content, expected_item_count=len(document.items))
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return content, etree.fromstring(archive.read("word/document.xml"))


_DRAWING_IDS = "//wp:docPr/@id | //wps:cNvPr/@id | //wpg:cNvPr/@id"


def _media_names(content: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return [name for name in archive.namelist() if name.startswith("word/media/")]


def _picture_paragraphs(root: etree._Element, label: str) -> list[etree._Element]:
    paragraphs: list[etree._Element] = root.xpath(
        f"//w:p[w:r/w:t[starts-with(., '{label}')]]",
        namespaces=_NAMESPACES,
    )
    return paragraphs


class TestStoredShapesReplaceThePicture:
    def test_group_shapes_are_written_as_an_inline_drawing_in_the_question_paragraph(
        self,
    ) -> None:
        content, root = _export((_ASSET_A, _stored_group_shapes()))

        (paragraph,) = _picture_paragraphs(root, "Se bild 1")
        (inline,) = paragraph.xpath(
            "./w:r/mc:AlternateContent/mc:Choice[@Requires='wpg']/w:drawing/wp:inline",
            namespaces=_NAMESPACES,
        )
        assert inline.xpath("./a:graphic/a:graphicData/wpg:wgp", namespaces=_NAMESPACES)
        written = "".join(inline.xpath(".//w:t/text()", namespaces=_NAMESPACES))
        for label in _LABELS:
            assert label in written
        assert (
            paragraph.xpath("./w:r/mc:AlternateContent/mc:Fallback", namespaces=_NAMESPACES) == []
        )
        assert root.xpath("//a:blip", namespaces=_NAMESPACES) == []
        assert _media_names(content) == []

    def test_the_picture_paragraph_keeps_the_picture_spacing(self) -> None:
        _, shape_root = _export((_ASSET_A, _stored_group_shapes()))
        _, plain_root = _export((_ASSET_A, None))

        (shape_paragraph,) = _picture_paragraphs(shape_root, "Se bild 1")
        (plain_paragraph,) = _picture_paragraphs(plain_root, "Se bild 1")
        spacing = "./w:pPr/w:spacing"
        assert dict(shape_paragraph.xpath(spacing, namespaces=_NAMESPACES)[0].attrib) == dict(
            plain_paragraph.xpath(spacing, namespaces=_NAMESPACES)[0].attrib
        )

    def test_two_pictures_get_unique_drawing_ids_and_no_word_revision_ids(self) -> None:
        shapes = _stored_group_shapes()
        _, root = _export((_ASSET_A, shapes), (_ASSET_B, shapes))

        doc_pr_ids = root.xpath("//wp:docPr/@id", namespaces=_NAMESPACES)
        assert len(doc_pr_ids) == 2
        every_shape_id = root.xpath(_DRAWING_IDS, namespaces=_NAMESPACES)
        assert len(every_shape_id) == 6  # two docPr and two shapes in each of two drawings
        assert len(every_shape_id) == len(set(every_shape_id))
        drawings = root.xpath("//w:drawing", namespaces=_NAMESPACES)
        assert len(drawings) == 2
        for drawing in drawings:
            assert drawing.xpath(".//@w14:paraId", namespaces=_NAMESPACES) == []
            assert drawing.xpath(".//@w14:textId", namespaces=_NAMESPACES) == []
            assert drawing.xpath(".//@wp14:anchorId", namespaces=_NAMESPACES) == []
            assert drawing.xpath(".//@wp14:editId", namespaces=_NAMESPACES) == []
            assert drawing.xpath(".//@*[starts-with(local-name(), 'rsid')]") == []
        assert set(every_shape_id).isdisjoint({"9001", "9101", "9102"})

    def test_shape_ids_stay_unique_beside_ordinary_pictures(self) -> None:
        shapes = _stored_group_shapes()
        content, root = _export((_ASSET_A, None), (_ASSET_B, shapes), (_ASSET_C, None))

        every_shape_id = root.xpath(_DRAWING_IDS, namespaces=_NAMESPACES)
        assert len(every_shape_id) == 5  # two plain docPr and the group's docPr and two shapes
        assert len(every_shape_id) == len(set(every_shape_id))
        assert len(root.xpath("//a:blip", namespaces=_NAMESPACES)) == 2
        assert len(_media_names(content)) == 1  # identical PNG bytes share one image part
        assert len(root.xpath("//mc:AlternateContent", namespaces=_NAMESPACES)) == 1

    def test_a_stored_anchor_is_written_as_an_inline(self) -> None:
        def to_anchor(drawing: etree._Element) -> None:
            (inline,) = drawing
            anchor = etree.Element(
                f"{{{_WP}}}anchor",
                {
                    "distT": "0",
                    "distB": "0",
                    "distL": "0",
                    "distR": "0",
                    "simplePos": "0",
                    "relativeHeight": "251658240",
                    "behindDoc": "0",
                    "locked": "0",
                    "layoutInCell": "1",
                    "allowOverlap": "1",
                    f"{{{_NAMESPACES['wp14']}}}anchorId": "2BABB811",
                },
                nsmap={"wp": _WP, "wp14": _NAMESPACES["wp14"]},
            )
            etree.SubElement(anchor, f"{{{_WP}}}simplePos", {"x": "0", "y": "0"})
            horizontal = etree.SubElement(anchor, f"{{{_WP}}}positionH", {"relativeFrom": "column"})
            etree.SubElement(horizontal, f"{{{_WP}}}posOffset").text = "100"
            vertical = etree.SubElement(
                anchor, f"{{{_WP}}}positionV", {"relativeFrom": "paragraph"}
            )
            etree.SubElement(vertical, f"{{{_WP}}}posOffset").text = "200"
            for child in list(inline):
                anchor.append(child)
                if child.tag == f"{{{_WP}}}effectExtent":
                    etree.SubElement(anchor, f"{{{_WP}}}wrapSquare", {"wrapText": "bothSides"})
            drawing.replace(inline, anchor)

        _, root = _export((_ASSET_A, _edited_shapes(to_anchor)))

        (drawing,) = root.xpath("//mc:Choice/w:drawing", namespaces=_NAMESPACES)
        (inline,) = drawing
        assert inline.tag == f"{{{_WP}}}inline"
        assert [child.tag.rpartition("}")[2] for child in inline] == [
            "extent",
            "effectExtent",
            "docPr",
            "cNvGraphicFramePr",
            "graphic",
        ]
        assert {name: inline.get(name) for name in ("distT", "distB", "distL", "distR")} == {
            "distT": "0",
            "distB": "0",
            "distL": "0",
            "distR": "0",
        }
        assert inline.get("simplePos") is None
        assert drawing.xpath(".//@wp14:anchorId", namespaces=_NAMESPACES) == []
        assert inline.xpath("./a:graphic//wpg:wgp", namespaces=_NAMESPACES)


def _add_embed(drawing: etree._Element) -> None:
    graphic_data = drawing.xpath(".//a:graphicData", namespaces=_NAMESPACES)[0]
    blip = etree.SubElement(
        graphic_data, f"{{{_NAMESPACES['a']}}}blip", {f"{{{_R}}}embed": "rId99"}, nsmap={"r": _R}
    )
    assert blip is not None


def _unknown_graphic(drawing: etree._Element) -> None:
    graphic_data = drawing.xpath(".//a:graphicData", namespaces=_NAMESPACES)[0]
    graphic_data.set("uri", "http://schemas.openxmlformats.org/drawingml/2006/chart")


class TestUnusableShapesWriteThePicture:
    @pytest.mark.parametrize(
        "stored",
        [
            pytest.param("<w:drawing xmlns:w=", id="malformed-xml"),
            pytest.param(
                f'<w:p xmlns:w="{_W}"><w:r><w:t>text</w:t></w:r></w:p>', id="root-is-not-a-drawing"
            ),
            pytest.param(_edited_shapes(_add_embed), id="relationship-reference"),
            pytest.param(_edited_shapes(_unknown_graphic), id="not-a-shape-graphic"),
        ],
    )
    def test_the_picture_is_written_instead(self, stored: str) -> None:
        content, root = _export((_ASSET_A, stored))

        assert len(root.xpath("//a:blip", namespaces=_NAMESPACES)) == 1
        assert root.xpath("//mc:AlternateContent", namespaces=_NAMESPACES) == []
        assert len(_media_names(content)) == 1
        assert root.xpath("//wpg:wgp", namespaces=_NAMESPACES) == []


_WPC = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
_NAMESPACES["wpc"] = _WPC
_SOURCE_NAMESPACES = (
    f'xmlns:w="{_W}" xmlns:wp="{_WP}" xmlns:a="{_NAMESPACES["a"]}" '
    f'xmlns:wpg="{_NAMESPACES["wpg"]}" xmlns:wps="{_NAMESPACES["wps"]}" xmlns:wpc="{_WPC}"'
)


def _rectangle(shape_id: int, name: str, x: int) -> str:
    return (
        f'<wps:wsp><wps:cNvPr id="{shape_id}" name="{name}"/><wps:cNvSpPr/><wps:spPr>'
        f'<a:xfrm><a:off x="{x}" y="0"/><a:ext cx="1000" cy="500"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></wps:spPr><wps:bodyPr/></wps:wsp>'
    )


def _connector(shape_id: int, start: int, end: int) -> str:
    return (
        f'<wps:wsp><wps:cNvPr id="{shape_id}" name="Pil"/><wps:cNvCnPr>'
        f'<a:stCxn id="{start}" idx="3"/><a:endCxn id="{end}" idx="1"/></wps:cNvCnPr><wps:spPr>'
        '<a:xfrm><a:off x="1000" y="250"/><a:ext cx="1000" cy="0"/></a:xfrm>'
        '<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom></wps:spPr>'
        "<wps:bodyPr/></wps:wsp>"
    )


def _drawing(graphic_uri: str, root: str, *, cx: int, cy: int) -> str:
    return (
        f"<w:drawing {_SOURCE_NAMESPACES}>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="7" name="Figur"/><wp:cNvGraphicFramePr/>'
        f'<a:graphic><a:graphicData uri="{graphic_uri}">{root}</a:graphicData></a:graphic>'
        "</wp:inline></w:drawing>"
    )


def _group_xml(children: str, *, cx: int = 3000, cy: int = 1000) -> str:
    return _drawing(
        _NAMESPACES["wpg"],
        "<wpg:wgp><wpg:cNvGrpSpPr/><wpg:grpSpPr><a:xfrm>"
        f'<a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="{cx}" cy="{cy}"/>'
        f"</a:xfrm></wpg:grpSpPr>{children}</wpg:wgp>",
        cx=cx,
        cy=cy,
    )


def _single_xml(*, cx: int, cy: int) -> str:
    return _drawing(
        _NAMESPACES["wps"],
        '<wps:wsp><wps:cNvPr id="3" name="Ensam"/><wps:cNvSpPr/><wps:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></wps:spPr><wps:bodyPr/></wps:wsp>',
        cx=cx,
        cy=cy,
    )


def _canvas_xml(*, cx: int, cy: int) -> str:
    return _drawing(
        _WPC,
        f"<wpc:wpc><wpc:bg/><wpc:whole/>{_rectangle(3, 'Duk', 0)}</wpc:wpc>",
        cx=cx,
        cy=cy,
    )


def _connected_group_xml(*, start: int, end: int) -> str:
    return _group_xml(
        _rectangle(100, "Vänster", 0) + _rectangle(101, "Höger", 2000) + _connector(102, start, end)
    )


def _connection_ids(drawing: etree._Element) -> tuple[list[str], list[str]]:
    starts: list[str] = drawing.xpath(".//a:stCxn/@id", namespaces=_NAMESPACES)
    ends: list[str] = drawing.xpath(".//a:endCxn/@id", namespaces=_NAMESPACES)
    return starts, ends


def _shape_id(drawing: etree._Element, name: str) -> str:
    ids: list[str] = drawing.xpath(f".//wps:cNvPr[@name='{name}']/@id", namespaces=_NAMESPACES)
    assert len(ids) == 1
    return ids[0]


class TestConnectorsKeepTheirShapes:
    def test_each_copy_connects_its_own_renumbered_rectangles(self) -> None:
        group = _connected_group_xml(start=100, end=101)
        _, root = _export((_ASSET_A, None), (_ASSET_B, group), (_ASSET_C, group))

        drawings = root.xpath("//mc:Choice/w:drawing", namespaces=_NAMESPACES)
        assert len(drawings) == 2
        for drawing in drawings:
            starts, ends = _connection_ids(drawing)
            assert starts == [_shape_id(drawing, "Vänster")]
            assert ends == [_shape_id(drawing, "Höger")]
        every_doc_pr_id = root.xpath("//wp:docPr/@id", namespaces=_NAMESPACES)
        assert len(every_doc_pr_id) == 3  # the plain picture and the two group copies
        every_id = root.xpath(_DRAWING_IDS, namespaces=_NAMESPACES)
        assert len(every_id) == len(set(every_id))

    def test_a_connection_naming_a_shape_outside_the_drawing_is_removed(self) -> None:
        _, root = _export((_ASSET_A, _connected_group_xml(start=999, end=101)))

        (drawing,) = root.xpath("//w:drawing", namespaces=_NAMESPACES)
        starts, ends = _connection_ids(drawing)
        assert starts == []
        assert ends == [_shape_id(drawing, "Höger")]


class TestWideDrawingsAreFittedNotReplaced:
    @pytest.mark.parametrize(
        ("stored", "root_path"),
        [
            pytest.param(
                lambda cx, cy: _group_xml(_rectangle(100, "Vänster", 0), cx=cx, cy=cy),
                ".//wpg:grpSpPr/a:xfrm/a:ext",
                id="group",
            ),
            pytest.param(
                lambda cx, cy: _single_xml(cx=cx, cy=cy),
                ".//wps:spPr/a:xfrm/a:ext",
                id="single-shape",
            ),
        ],
    )
    def test_a_wide_drawing_is_scaled_to_the_text_width_keeping_its_aspect(
        self, stored: Callable[[int, int], str], root_path: str
    ) -> None:
        limit = int(Mm(TEXT_WIDTH_MM))
        cx, cy = limit + 1000, 1234567
        content, root = _export((_ASSET_A, stored(limit - 1000, cy)), (_ASSET_B, stored(cx, cy)))

        assert root.xpath("//a:blip", namespaces=_NAMESPACES) == []
        assert _media_names(content) == []
        control, wide = root.xpath("//wp:inline", namespaces=_NAMESPACES)
        assert control.xpath("./wp:extent/@cx", namespaces=_NAMESPACES) == [str(limit - 1000)]
        (extent,) = wide.xpath("./wp:extent", namespaces=_NAMESPACES)
        assert int(extent.get("cx", "")) == limit
        expected_cy = cy * limit / cx
        assert abs(int(extent.get("cy", "")) - expected_cy) <= 1
        (box,) = wide.xpath(root_path, namespaces=_NAMESPACES)
        assert int(box.get("cx", "")) == limit
        assert abs(int(box.get("cy", "")) - expected_cy) <= 1
        assert control.xpath(root_path + "/@cy", namespaces=_NAMESPACES) == [str(cy)]

    def test_a_wide_group_keeps_its_child_coordinate_space(self) -> None:
        limit = int(Mm(TEXT_WIDTH_MM))
        _, root = _export((_ASSET_A, _group_xml(_rectangle(100, "Vänster", 0), cx=limit + 1000)))

        (transform,) = root.xpath(".//wpg:grpSpPr/a:xfrm", namespaces=_NAMESPACES)
        (child_extent,) = transform.xpath("./a:chExt", namespaces=_NAMESPACES)
        assert child_extent.get("cx") == str(limit + 1000)
        assert child_extent.get("cy") == "1000"

    def test_a_wide_canvas_keeps_its_source_size_and_stays_editable(self) -> None:
        limit = int(Mm(TEXT_WIDTH_MM))
        content, root = _export((_ASSET_A, _canvas_xml(cx=limit + 1000, cy=777)))

        assert root.xpath("//a:blip", namespaces=_NAMESPACES) == []
        assert _media_names(content) == []
        (extent,) = root.xpath("//wp:inline/wp:extent", namespaces=_NAMESPACES)
        assert (extent.get("cx"), extent.get("cy")) == (str(limit + 1000), "777")
        assert len(root.xpath("//wpc:wpc", namespaces=_NAMESPACES)) == 1
