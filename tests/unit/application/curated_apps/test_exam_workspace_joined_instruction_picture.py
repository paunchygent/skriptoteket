"""F2 joined instructions: a picture inside an item's own instruction keeps its exact place.

Real assembly of source chunks inside one question, plus the real QTI package writer: the
joined instruction's wording and picture stay in source order in the item body, the picture
reaches the packaged item once, a picture the item's body already places is not inserted
again only when its complete paragraph matches, and shared headings retain their pictures
through deterministic points-label and question-number removal.
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    ConversionTarget,
    merge_conversion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
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
    return {
        "kind": "text",
        "text": text,
        "accepted_values": [],
        "asset_id": None,
    }


def _asset(asset_id: str) -> dict[str, object]:
    return {
        "kind": "asset",
        "text": None,
        "accepted_values": [],
        "asset_id": asset_id,
    }


def _converted(anchor: str, text: str = "svar") -> AlignedItem:
    return aligned_native_item(
        ProducedItem.model_validate(
            {
                "source_anchors": [anchor],
                "outcome": "converted",
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "body": [{"segments": [_text(text)]}],
                "points": 1,
                "choices": [],
            }
        ),
        language="sv",
        foreign_chunks=(),
    )


def _joined_chunks() -> tuple[DocxChunk, ...]:
    return (
        DocxChunk("body:0001", "paragraph", "Fråga 1. Vad ser du?", "Fråga 1. Vad ser du?"),
        DocxChunk("body:0002", "paragraph", _JOINED_TEXT, _JOINED_TEXT, (_joined_picture(),)),
        DocxChunk("body:0003", "paragraph", "a) en katt", "a) en katt"),
    )


def _joined_item(paragraphs: _PARAGRAPHS) -> AlignedItem:
    return aligned_native_item(
        ProducedItem.model_validate(
            {
                "source_anchors": ["body:0001"],
                "outcome": "converted",
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "body": [{"segments": segments} for segments in paragraphs],
                "points": 1,
                "choices": [],
            }
        ),
        chunks=_joined_chunks(),
        language="sv",
        foreign_chunks=(),
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
        item_path = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ElementTree.fromstring(archive.read(item_path))
        images = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img"]
        assert len(images) == 1
        paragraph = next(node for node in root.iter() if images[0] in list(node))
        assert paragraph.text == "Betrakta diagrammet: "
        assert images[0].tail == "Svara sedan."
        resources = [name for name in archive.namelist() if archive.read(name) == _png()]
        assert len(resources) == 1
        assert images[0].attrib["src"].rsplit("/", 1)[-1] == resources[0].rsplit("/", 1)[-1]


def test_a_reply_paragraph_aligned_to_the_instruction_shows_its_source_occurrence():
    # The reply rewords the instruction around its picture; the alignment maps the line to
    # the instruction chunk, so the line is that chunk and shows in its source form, once.
    asset_id = _joined_picture().asset_id
    built = _built(
        item_paragraphs=[
            [_text("Betrakta diagrammet: "), _asset(asset_id), _text(_ALT_TEXT)],
            [_text("a) en katt")],
        ]
    )
    (item,) = built.document.items

    assert body_asset_ids(item.body) == (asset_id,)
    assert body_text_lines(item.body) == (_JOINED_TEXT, "a) en katt")
    assert item.body[0] == source_paragraph(_joined_chunks()[1])


@pytest.mark.parametrize("separate_instructions", [False, True])
@pytest.mark.parametrize("already_delivered", [False, True])
def test_a_repeated_source_paragraph_keeps_both_picture_occurrences(
    separate_instructions: bool, already_delivered: bool
):
    chunks = _joined_chunks()
    duplicate = DocxChunk(
        "body:0002b", "paragraph", _JOINED_TEXT, _JOINED_TEXT, (_joined_picture(),)
    )
    instructions = (
        (
            _JOINED_INSTRUCTION,
            ProducedMetadata(text=_JOINED_TEXT, source_anchors=(duplicate.anchor,)),
        )
        if separate_instructions
        else (ProducedMetadata(text=_JOINED_TEXT, source_anchors=("body:0002", duplicate.anchor)),)
    )
    paragraphs = [[_text("a) en katt")]]
    if already_delivered:
        paragraphs.insert(
            0,
            [
                _text("Betrakta diagrammet: "),
                _asset(_joined_picture().asset_id),
                _text("Svara sedan."),
            ],
        )
    built = assemble_build_result(
        document_id=uuid4(),
        filename="repeated.docx",
        source_sha256="0" * 64,
        chunks=(*chunks[:2], duplicate, chunks[2]),
        accepted=((_joined_item(paragraphs), ("body:0001", "body:0003")),),
        review_reasons={},
        instructions=instructions,
        questions=(("body:0001", "body:0003"),),
    )
    assert body_asset_ids(built.document.items[0].body) == (_joined_picture().asset_id,) * 2


def test_a_shared_heading_keeps_its_picture_while_its_wording_is_the_source_text():
    built = _built_headed()

    (parent,) = built.document.parents
    assert body_text_lines(parent.instruction) == (_HEADING_TEXT,)
    assert body_asset_ids(parent.instruction) == (_end_picture(_HEADING_TEXT).asset_id,)
    assert parent.item_ids == tuple(item.item_id for item in built.document.items)
    assert [asset.asset_id for asset in built.document.assets] == [
        _end_picture(_HEADING_TEXT).asset_id
    ]


@pytest.mark.parametrize("text", [_JOINED_TEXT, ""])
def test_identical_picture_paragraphs_at_distinct_shared_source_anchors_both_land(text: str):
    image = _joined_picture() if text else _end_picture(text)
    chunks = (
        DocxChunk("body:0001", "paragraph", "Prov", "Prov"),
        DocxChunk("body:0002", "paragraph", text, text, (image,)),
        DocxChunk("body:0002b", "paragraph", text, text, (image,)),
        DocxChunk("body:0003", "paragraph", "Fråga 1. Vad?", "Fråga 1. Vad?"),
        DocxChunk("body:0004", "paragraph", "Fråga 2. Hur?", "Fråga 2. Hur?"),
    )
    built = assemble_build_result(
        document_id=uuid4(),
        filename="parent.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=(
            (_converted("body:0003"), ("body:0003",)),
            (_converted("body:0004"), ("body:0004",)),
        ),
        review_reasons={},
        instructions=(
            ProducedMetadata(text=_JOINED_TEXT, source_anchors=("body:0002", "body:0002b")),
        ),
        governed={"body:0002": frozenset({"body:0003", "body:0004"})},
        questions=(("body:0003",), ("body:0004",)),
    )
    (parent,) = built.document.parents
    assert body_asset_ids(parent.instruction) == (_joined_picture().asset_id,) * 2
    assert parent.instruction[0] == parent.instruction[1]


def test_the_assembled_parent_picture_survives_a_no_op_progressive_merge():
    built = _built_headed()
    merged = merge_conversion(
        head=built.document, progress=ConversionProgress(), target=ConversionTarget(units=())
    )
    assert merged.document.parents == built.document.parents
    assert merged.document.assets == built.document.assets


def test_a_shared_heading_with_points_keeps_its_picture_after_normalized_wording():
    built = _built_headed(_POINTS_HEADING_TEXT)
    (parent,) = built.document.parents
    assert body_text_lines(parent.instruction) == (_HEADING_TEXT,)
    assert [segment.kind for segment in parent.instruction[0].segments] == ["text", "asset"]
    assert body_asset_ids(parent.instruction) == (_end_picture(_POINTS_HEADING_TEXT).asset_id,)
    package, _ = build_native_examnet_qti_package(
        built.document,
        package_name="points",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id=built.assets_by_id,
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        path = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ElementTree.fromstring(archive.read(path))
        (image,) = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img"]
        paragraph = next(node for node in root.iter() if image in list(node))
        assert paragraph.text == _HEADING_TEXT
        assert not (image.tail or "").strip()


def test_echoed_instruction_text_does_not_replace_its_positioned_picture_content():
    built = _built(item_paragraphs=[[_text(_JOINED_TEXT)], [_text("a) en katt")]])
    (item,) = built.document.items
    assert source_paragraph(_joined_chunks()[1]) in item.body
    assert body_asset_ids(item.body) == (_joined_picture().asset_id,)
    package, _ = build_native_examnet_qti_package(
        built.document,
        package_name="echoed",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id=built.assets_by_id,
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        path = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ElementTree.fromstring(archive.read(path))
        (image,) = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "img"]
        paragraph = next(node for node in root.iter() if image in list(node))
        assert paragraph.text == "Betrakta diagrammet: "
        assert image.tail == "Svara sedan."


@pytest.mark.parametrize("offset", [0, 8, 17, 23, 31])
def test_heading_normalization_maps_interior_and_removed_text_picture_positions(offset: int):
    text = "Fråga 1. Betrakta   diagrammet, 8 poäng"
    image = DocxImage(_png(), "image/png", offset=offset, marked_offset=offset)
    heading = DocxChunk("body:0002", "heading", text, text, (image,))
    chunks = (
        DocxChunk("body:0001", "paragraph", "Prov", "Prov"),
        heading,
        DocxChunk("body:0003", "paragraph", "a) en katt", "a) en katt"),
    )
    built = assemble_build_result(
        document_id=uuid4(),
        filename="heading.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=((_converted("body:0003", text), ("body:0002", "body:0003")),),
        review_reasons={},
        questions=(("body:0002", "body:0003"),),
    )
    (item,) = built.document.items
    assert body_asset_ids(item.body) == (image.asset_id,)
    shown = item.body[0]
    assert body_text_lines((shown,)) == ("Betrakta diagrammet",)
    expected_offset = {0: 0, 8: 0, 17: 8, 23: 12, 31: 19}[offset]
    before = "".join(
        segment.text
        for segment in shown.segments[
            : next(i for i, segment in enumerate(shown.segments) if segment.kind == "asset")
        ]
        if segment.kind == "text"
    )
    assert len(before) == expected_offset


@pytest.mark.parametrize("text", ["Fråga 1. (2 p)", "(2 p)", ""])
def test_heading_without_retained_wording_still_delivers_its_picture(text: str):
    image = _end_picture(text)
    built = assemble_build_result(
        document_id=uuid4(),
        filename="heading.docx",
        source_sha256="0" * 64,
        chunks=(
            DocxChunk("body:0001", "paragraph", "Prov", "Prov"),
            DocxChunk("body:0002", "heading", text, text, (image,)),
            DocxChunk("body:0003", "paragraph", "Svara.", "Svara."),
        ),
        accepted=((_converted("body:0003", "Svara."), ("body:0002", "body:0003")),),
        review_reasons={},
        questions=(("body:0002", "body:0003"),),
    )
    assert built.document.items[0].body[0].segments == (
        NativeAssetSegment(asset_id=image.asset_id),
    )


@pytest.mark.parametrize("split_text", [False, True])
def test_a_complete_positioned_instruction_already_delivered_is_not_repeated(split_text: bool):
    asset_id = _joined_picture().asset_id
    before = (
        [_text("Betrakta "), _text("diagrammet: ")]
        if split_text
        else [_text("Betrakta diagrammet: ")]
    )
    built = _built(
        item_paragraphs=[
            [*before, _asset(asset_id), _text("Svara sedan.")],
            [_text("a) en katt")],
        ]
    )
    (item,) = built.document.items
    assert body_asset_ids(item.body) == (asset_id,)
    assert body_text_lines(item.body) == (_JOINED_TEXT, "a) en katt")
