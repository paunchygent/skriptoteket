"""Native projection of DOCX pictures: carriers, exact places and the asset manifest (D2)."""

from dataclasses import replace
from typing import Literal
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_build_assets import asset_manifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxMissingImage,
    asset_id_for,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import (
    missing_picture_reasons,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

_PNG = b"picture-one"
_JPEG = b"picture-two"


def _image(
    payload: bytes,
    media_type: Literal["image/png", "image/jpeg"] = "image/png",
    offset: int = 0,
) -> DocxImage:
    return DocxImage(
        payload=payload,
        media_type=media_type,
        offset=offset,
        marked_offset=offset,
    )


def _chunk(
    anchor: str,
    text: str,
    images: tuple[DocxImage, ...] = (),
    missing: tuple[DocxMissingImage, ...] = (),
) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text, images, missing)


def _missing(reference: str, media_type: str, offset: int = 0) -> DocxMissingImage:
    return DocxMissingImage(
        reference=reference, media_type=media_type, offset=offset, marked_offset=offset
    )


def _produced(segments: list[dict[str, object]]) -> ProducedItem:
    return ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001"],
            "outcome": "converted",
            "conflict_kind": None,
            "review_reason": None,
            "kind": "free_text",
            "printed_label": None,
            "key_source": None,
            "facit_text": None,
            "body": [{"segments": segments}],
            "points": 1,
            "choices": [],
            "match_left": [],
            "match_right": [],
            "match_pairs": [],
            "criteria": [],
        }
    )


def test_review_source_item_splits_text_around_each_picture_place() -> None:
    image = _image(_PNG, offset=2)
    chunk = _chunk("body:0001", "ABCDEF", (image,))

    item = review_source_item((chunk,), "Granska.")

    (paragraph,) = item.body
    assert paragraph.segments == (
        NativeTextSegment(text="AB", marks=()),
        NativeAssetSegment(asset_id=image.asset_id),
        NativeTextSegment(text="CDEF", marks=()),
    )


def test_review_source_item_keeps_a_repeated_picture_twice() -> None:
    image = _image(_PNG, offset=1)
    chunk = _chunk("body:0001", "ABCD", (image, image))

    item = review_source_item((chunk,), "Granska.")

    (paragraph,) = item.body
    assert paragraph.segments == (
        NativeTextSegment(text="A", marks=()),
        NativeAssetSegment(asset_id=image.asset_id),
        NativeAssetSegment(asset_id=image.asset_id),
        NativeTextSegment(text="BCD", marks=()),
    )


def test_native_item_maps_the_model_carrier_to_the_source_picture() -> None:
    image = _image(_PNG)
    chunk = _chunk("body:0001", "Se bilden", (image,))
    produced = _produced(
        [
            {"kind": "text", "text": "Se bilden", "accepted_values": []},
            {
                "kind": "asset",
                "text": None,
                "accepted_values": [],
                "asset_id": image.asset_id,
            },
        ]
    )

    item = aligned_native_item(produced, chunks=(chunk,), language="sv", foreign_chunks=()).item

    (paragraph,) = item.body
    assert paragraph.segments == (
        NativeTextSegment(text="Se bilden", marks=()),
        NativeAssetSegment(asset_id=image.asset_id),
    )
    assert item.body_asset_ids() == (image.asset_id,)


def test_native_item_rejects_a_picture_the_source_does_not_carry() -> None:
    produced = _produced(
        [
            {
                "kind": "asset",
                "text": None,
                "accepted_values": [],
                "asset_id": asset_id_for(b"invented"),
            }
        ]
    )

    with pytest.raises(ValueError):
        aligned_native_item(produced, chunks=(), language="sv", foreign_chunks=()).item


def test_manifest_carries_a_retry_only_picture_without_exporting_it() -> None:
    body_image = _image(_PNG)
    source_image = _image(_JPEG, media_type="image/jpeg")
    chunk = _chunk("body:0001", "Fråga", (body_image,))
    # The facit chunk that carries the retry-only picture is part of the document's chunks.
    source_chunk = _chunk("body:0002", "Facit", (source_image,))
    produced = _produced(
        [
            {"kind": "text", "text": "Fråga", "accepted_values": []},
            {
                "kind": "asset",
                "text": None,
                "accepted_values": [],
                "asset_id": body_image.asset_id,
            },
        ]
    )
    item = aligned_native_item(
        produced, chunks=(chunk,), language="sv", foreign_chunks=()
    ).item.model_copy(
        update={
            "retry_source": NativeExamRetrySource(
                chunks=(
                    NativeExamRetryChunk(
                        anchor="body:0001",
                        kind="paragraph",
                        text="Fråga",
                        marked_text="Fråga",
                        images=(
                            NativeExamRetryImage(
                                asset_id=source_image.asset_id,
                                offset=0,
                                marked_offset=0,
                            ),
                        ),
                        runs=(),
                        paragraphs=(),
                    ),
                ),
                owned_context_anchors=(),
                key_chunks=(),
                context_chunks=(),
                label_kind=NativeExamItemKind.FREE_TEXT,
            )
        }
    )

    assets, payloads = asset_manifest((item,), (chunk, source_chunk))

    assert {asset.asset_id for asset in assets} == {body_image.asset_id, source_image.asset_id}
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(item,),
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    (qti_item,) = native_exam_to_examnet_qti_items(document, assets_by_id=payloads)
    assert [resource.source_reference for resource in qti_item.image_resources] == [
        body_image.asset_id
    ]


def test_manifest_drops_a_picture_no_item_references() -> None:
    used = _image(_PNG)
    unused = _image(_JPEG, media_type="image/jpeg")
    chunk = _chunk("body:0001", "Fråga", (used, unused))
    produced = _produced(
        [
            {"kind": "text", "text": "Fråga", "accepted_values": []},
            {
                "kind": "asset",
                "text": None,
                "accepted_values": [],
                "asset_id": used.asset_id,
            },
        ]
    )
    item = aligned_native_item(produced, chunks=(chunk,), language="sv", foreign_chunks=()).item

    assets, payloads = asset_manifest((item,), (chunk,))

    assert [asset.asset_id for asset in assets] == [used.asset_id]
    assert set(payloads) == {used.asset_id}


def test_manifest_carries_the_shape_markup_of_a_drawn_picture_to_its_asset() -> None:
    drawn = replace(_image(_PNG), docx_shapes="<w:drawing/>")
    plain = _image(_JPEG, media_type="image/jpeg")
    chunk = _chunk("body:0001", "Fråga", (drawn, plain))
    produced = _produced(
        [
            {"kind": "text", "text": "Fråga", "accepted_values": []},
            {"kind": "asset", "text": None, "accepted_values": [], "asset_id": drawn.asset_id},
            {"kind": "asset", "text": None, "accepted_values": [], "asset_id": plain.asset_id},
        ]
    )
    item = aligned_native_item(produced, chunks=(chunk,), language="sv", foreign_chunks=()).item

    assets, _ = asset_manifest((item,), (chunk,))

    shapes = {asset.asset_id: asset.docx_shapes for asset in assets}
    assert shapes == {drawn.asset_id: "<w:drawing/>", plain.asset_id: None}


def test_native_item_refuses_a_question_whose_source_picture_is_missing() -> None:
    chunk = _chunk(
        "body:0001",
        "Se bilden",
        missing=(_missing("/word/media/figur.emf", "image/x-emf"),),
    )
    produced = _produced(
        [
            {
                "kind": "text",
                "text": "Se bilden",
                "accepted_values": [],
            }
        ]
    )

    with pytest.raises(ValueError) as raised:
        aligned_native_item(produced, chunks=(chunk,), language="sv", foreign_chunks=()).item

    assert "unresolved source pictures" in str(raised.value)
    assert "/word/media/figur.emf" in str(raised.value)


def test_review_source_item_names_a_missing_picture_beside_its_reason() -> None:
    missing = _missing("/word/media/figur.wmf", "image/x-wmf", offset=2)
    chunk = _chunk("body:0001", "AABB", missing=(missing,))

    item = review_source_item((chunk,), "Granska.")

    assert item.review.reasons[0] == "Granska."
    assert item.review.reasons[1] == (
        "Bilden /word/media/figur.wmf (image/x-wmf) kan inte visas i provet. "
        "Granska frågan manuellt."
    )
    (paragraph,) = item.body
    assert paragraph.segments == (
        NativeTextSegment(text="AA", marks=()),
        NativeTextSegment(text="[Bild saknas: /word/media/figur.wmf (image/x-wmf)]", marks=()),
        NativeTextSegment(text="BB", marks=()),
    )


def test_missing_picture_reasons_name_each_picture_once() -> None:
    first = _missing("/word/media/figur.emf", "image/x-emf")
    second = _missing("/word/media/tabell.wmf", "image/x-wmf")
    chunk = _chunk("body:0001", "Bilder", missing=(first, second, first))

    reasons = missing_picture_reasons((chunk,))

    assert len(reasons) == 2
    assert reasons[0].startswith("Bilden /word/media/figur.emf")
    assert reasons[1].startswith("Bilden /word/media/tabell.wmf")
    assert missing_picture_reasons((_chunk("body:0001", "Text"),)) == ()
