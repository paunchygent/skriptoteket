"""F2 joined instructions: a picture inside an item's own instruction keeps its exact place.

Real assembly of source chunks inside one question, plus the real QTI package writer: the
joined instruction's wording and picture stay in source order in the item body, the picture
reaches the packaged item once, a picture the item's body already places is not inserted
again, and a shared heading keeps its picture only while its shown wording is the source
text. A heading whose points label or number rewrites the wording is refused with a named
failure instead of moving the picture.
"""

import zipfile
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree

import pytest
from PIL import Image

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    assemble_build_result,
    native_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_text_lines,
    source_paragraph,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

_JOINED_TEXT = "Betrakta diagrammet: Svara sedan."
_JOINED_INSTRUCTION = ProducedMetadata(text=_JOINED_TEXT, source_anchors=("body:0002",))
_HEADING_TEXT = "Del 2: Satsdelar"
_POINTS_HEADING_TEXT = "Del 2: Satsdelar, 8 poäng"
_ALT_TEXT = "Något annat."
_PARAGRAPHS = list[list[dict[str, object]]]


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (8, 4), (25, 130, 60, 180)).save(buffer, format="PNG")
    return buffer.getvalue()


def _joined_picture() -> DocxImage:
    offset = _JOINED_TEXT.index("Svara")
    return DocxImage(_png(), "image/png", offset=offset, marked_offset=offset)


def _end_picture(text: str) -> DocxImage:
    return DocxImage(_png(), "image/png", offset=len(text), marked_offset=len(text))


def _text(text: str) -> dict[str, object]:
    return {"kind": "text", "text": text, "accepted_values": [], "asset_id": None}


def _asset(asset_id: str) -> dict[str, object]:
    return {"kind": "asset", "text": None, "accepted_values": [], "asset_id": asset_id}


def _converted(anchor: str, text: str = "svar") -> NativeExamItem:
    return native_item(
        ProducedItem.model_validate(
            {
                "source_anchors": [anchor],
                "outcome": "converted",
                "review_reason": None,
                "kind": "free_text",
                "body": [{"segments": [_text(text)]}],
                "points": 1,
                "choices": [],
            }
        )
    )


def _joined_chunks() -> tuple[DocxChunk, ...]:
    return (
        DocxChunk("body:0001", "paragraph", "Fråga 1. Vad ser du?", "Fråga 1. Vad ser du?"),
        DocxChunk("body:0002", "paragraph", _JOINED_TEXT, _JOINED_TEXT, (_joined_picture(),)),
        DocxChunk("body:0003", "paragraph", "a) en katt", "a) en katt"),
    )


def _joined_item(paragraphs: _PARAGRAPHS) -> NativeExamItem:
    return native_item(
        ProducedItem.model_validate(
            {
                "source_anchors": ["body:0001"],
                "outcome": "converted",
                "review_reason": None,
                "kind": "free_text",
                "body": [{"segments": segments} for segments in paragraphs],
                "points": 1,
                "choices": [],
            }
        ),
        chunks=_joined_chunks(),
    )


def _built(*, item_paragraphs: _PARAGRAPHS | None = None) -> DocxBuildResult:
    chunks = _joined_chunks()
    item = _joined_item(item_paragraphs or [[_text("a) en katt")]])
    return assemble_build_result(
        document_id=uuid4(),
        filename="joined.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=((item, ("body:0001", "body:0003")),),
        review_reasons={},
        instructions=(_JOINED_INSTRUCTION,),
        questions=(("body:0001", "body:0003"),),
    )


def _built_headed(heading_text: str = _HEADING_TEXT) -> DocxBuildResult:
    chunks = (
        DocxChunk("body:0001", "paragraph", "Prov i svenska", "Prov i svenska"),
        DocxChunk(
            "body:0002", "heading", heading_text, heading_text, (_end_picture(heading_text),)
        ),
        DocxChunk(
            "body:0003", "paragraph", "Fråga 1. Vad betyder alpha?", "Fråga 1. Vad betyder alpha?"
        ),
        DocxChunk(
            "body:0004", "paragraph", "Fråga 2. Vad betyder beta?", "Fråga 2. Vad betyder beta?"
        ),
    )
    return assemble_build_result(
        document_id=uuid4(),
        filename="headed.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=(
            (_converted("body:0003"), ("body:0003",)),
            (_converted("body:0004"), ("body:0004",)),
        ),
        review_reasons={},
        questions=(("body:0003",), ("body:0004",)),
    )


def test_a_joined_instruction_keeps_its_picture_between_its_wording():
    built = _built()
    (item,) = built.document.items
    asset_id = _joined_picture().asset_id

    assert built.document.parents == ()
    assert body_asset_ids(item.body) == (asset_id,)
    assert body_text_lines(item.body) == (_JOINED_TEXT, "a) en katt")
    assert item.body[0] == source_paragraph(_joined_chunks()[1])
    assert [segment.kind for segment in item.body[0].segments] == ["text", "asset", "text"]
    assert item.body[0].segments[1] == NativeAssetSegment(asset_id=asset_id)
    assert [asset.asset_id for asset in built.document.assets] == [asset_id]


def test_the_joined_picture_reaches_the_packaged_item_at_its_place():
    built = _built()
    package, _report = build_native_examnet_qti_package(
        built.document,
        package_name="joined",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id=built.assets_by_id,
    )

    with zipfile.ZipFile(BytesIO(package)) as archive:
        item_path = next(name for name in archive.namelist() if name.startswith("items/"))
        root = ElementTree.fromstring(archive.read(item_path))
        images = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img"]
        assert len(images) == 1
        paragraph = next(node for node in root.iter() if images[0] in list(node))
        assert paragraph.text == "Betrakta diagrammet: "
        assert images[0].tail == "Svara sedan."
        resources = [name for name in archive.namelist() if archive.read(name) == _png()]
        assert len(resources) == 1
        assert images[0].attrib["src"].rsplit("/", 1)[-1] == resources[0].rsplit("/", 1)[-1]


def test_a_picture_the_item_body_already_places_is_not_inserted_again():
    asset_id = _joined_picture().asset_id
    built = _built(
        item_paragraphs=[
            [_text("Betrakta diagrammet: "), _asset(asset_id), _text(_ALT_TEXT)],
            [_text("a) en katt")],
        ]
    )
    (item,) = built.document.items

    assert body_asset_ids(item.body) == (asset_id,)
    assert body_text_lines(item.body) == (
        "Betrakta diagrammet: Något annat.",
        _JOINED_TEXT,
        "a) en katt",
    )
    assert not any(
        isinstance(segment, NativeAssetSegment)
        for paragraph in item.body[1:]
        for segment in paragraph.segments
    )


def test_a_shared_heading_keeps_its_picture_while_its_wording_is_the_source_text():
    built = _built_headed()

    (parent,) = built.document.parents
    assert body_text_lines(parent.instruction) == (_HEADING_TEXT,)
    assert body_asset_ids(parent.instruction) == (_end_picture(_HEADING_TEXT).asset_id,)
    assert parent.item_ids == tuple(item.item_id for item in built.document.items)
    assert [asset.asset_id for asset in built.document.assets] == [
        _end_picture(_HEADING_TEXT).asset_id
    ]


def test_a_shared_heading_whose_wording_is_rewritten_fails_closed():
    with pytest.raises(ValueError, match="heading pictures have no faithful place: body:0002"):
        _built_headed(_POINTS_HEADING_TEXT)
