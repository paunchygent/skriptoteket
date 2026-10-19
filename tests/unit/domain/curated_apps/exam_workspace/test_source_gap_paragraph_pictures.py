"""Gap-paragraph picture placement (TASK-SKRIPT-39-04-16 D6)."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_provenance import (
    ChunkProvenance,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    chunk,
    gap,
    item,
    picture,
    text,
)

pytestmark = pytest.mark.unit


def test_pictures_in_returns_each_place_and_asset_id_in_source_order():
    first = DocxImage(payload=b"first", media_type="image/png", offset=3, marked_offset=3)
    second = DocxImage(payload=b"second", media_type="image/png", offset=0, marked_offset=0)
    provenance = ChunkProvenance()
    provenance.add(10, chunk("body:0001", "abc def", images=(first, second)))

    assert provenance.pictures_in(10, 17) == [(10, second.asset_id), (13, first.asset_id)]
    assert provenance.pictures_in(11, 13) == [(13, first.asset_id)]
    assert provenance.pictures_in(11, 12) == []
    assert provenance.pictures_in(13, 14) == [(13, first.asset_id)]


def test_a_source_picture_before_the_label_stands_first_in_the_built_paragraph():
    image = DocxImage(payload=b"figure", media_type="image/png", offset=0, marked_offset=0)
    chunks = (chunk("body:0001", "1. The answer is ___.", images=(image,)),)
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("The answer is "),
                    gap(),
                    text("."),
                    picture(image.asset_id),
                ]
            }
        ],
        printed_label="1",
    )

    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item

    segments = result.body[0].segments
    assert [segment.kind for segment in segments] == ["asset", "text", "gap", "text"]
    assert isinstance(segments[0], NativeAssetSegment)
    assert segments[0].asset_id == image.asset_id
    assert body_plain_text(result.body) == "The answer is [___]."


def test_a_mid_text_source_picture_splits_the_text_at_its_source_place():
    image = DocxImage(payload=b"figure", media_type="image/png", offset=10, marked_offset=10)
    chunks = (chunk("body:0001", "1. Alpha beta ___ gamma.", images=(image,)),)
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("Alpha beta "),
                    gap(),
                    text(" gamma."),
                    picture(image.asset_id),
                ]
            }
        ],
        printed_label="1",
    )

    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item

    segments = result.body[0].segments
    assert [segment.kind for segment in segments] == ["text", "asset", "text", "gap", "text"]
    assert isinstance(segments[1], NativeAssetSegment)
    assert segments[1].asset_id == image.asset_id
    assert body_plain_text(result.body) == "Alpha beta [___] gamma."


def test_a_reply_that_drops_the_source_picture_raises():
    image = DocxImage(payload=b"figure", media_type="image/png", offset=0, marked_offset=0)
    chunks = (chunk("body:0001", "1. The answer is ___.", images=(image,)),)
    produced = item(
        chunks,
        [{"segments": [text("The answer is "), gap(), text(".")]}],
        printed_label="1",
    )

    with pytest.raises(FormattingTransferError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())

    assert str(raised.value) == "cannot rebuild picture placement"


def test_a_reply_that_adds_a_picture_the_source_paragraph_lacks_raises():
    # The picture stands in a later paragraph of the same source chunk: its provenance
    # keeps it in the gap paragraph's group but outside the unit's own span.
    image = DocxImage(payload=b"elsewhere", media_type="image/png", offset=19, marked_offset=19)
    text_value = "The answer is ___.\nSee the figure."
    chunk_value = DocxChunk(
        "body:0001",
        "paragraph",
        text_value,
        text_value,
        images=(image,),
        runs=(DocxSourceRun(0, text_value, ()),),
        paragraphs=(
            DocxSourceParagraph(0, "The answer is ___."),
            DocxSourceParagraph(19, "See the figure."),
        ),
    )
    chunks = (chunk_value,)
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("The answer is "),
                    gap(),
                    text("."),
                    picture(image.asset_id),
                ]
            }
        ],
    )

    with pytest.raises(FormattingTransferError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())

    assert str(raised.value) == "cannot rebuild picture placement"


def test_a_trailing_picture_after_the_final_character_belongs_to_the_paragraph():
    source = "2. Describe the ____ rock cycle."
    image = DocxImage(payload=b"figure", media_type="image/png", offset=32, marked_offset=32)
    chunks = (chunk("body:0001", source, images=(image,)),)
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("Describe the "),
                    gap(),
                    text(" rock cycle."),
                    picture(image.asset_id),
                ]
            }
        ],
        printed_label="2",
    )

    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item

    segments = result.body[0].segments
    assert [segment.kind for segment in segments] == ["text", "gap", "text", "asset"]
    assert isinstance(segments[3], NativeAssetSegment)
    assert segments[3].asset_id == image.asset_id
    assert body_plain_text(result.body) == "Describe the [___] rock cycle."


def test_a_reply_that_drops_the_trailing_picture_raises():
    source = "2. Describe the ____ rock cycle."
    image = DocxImage(payload=b"figure", media_type="image/png", offset=32, marked_offset=32)
    chunks = (chunk("body:0001", source, images=(image,)),)
    produced = item(
        chunks,
        [{"segments": [text("Describe the "), gap(), text(" rock cycle.")]}],
        printed_label="2",
    )

    with pytest.raises(FormattingTransferError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())

    assert str(raised.value) == "cannot rebuild picture placement"


def test_pictures_in_includes_a_picture_at_end_but_not_beyond():
    image = DocxImage(payload=b"figure", media_type="image/png", offset=5, marked_offset=5)
    provenance = ChunkProvenance()
    provenance.add(10, chunk("body:0001", "abcde", images=(image,)))

    assert provenance.pictures_in(10, 15) == [(15, image.asset_id)]
    assert provenance.pictures_in(10, 14) == []
    assert provenance.pictures_in(10, 16) == [(15, image.asset_id)]


def _aba_images():
    first_a = DocxImage(payload=b"beta-figure-b", media_type="image/png", offset=7, marked_offset=7)
    middle_b = DocxImage(payload=b"figure-a-red", media_type="image/png", offset=7, marked_offset=7)
    second_a = DocxImage(
        payload=b"beta-figure-b", media_type="image/png", offset=7, marked_offset=7
    )
    assert middle_b.asset_id < first_a.asset_id
    assert second_a.asset_id == first_a.asset_id
    return first_a, middle_b, second_a


def _built_asset_ids(paragraph):
    return [segment.asset_id for segment in paragraph.segments if segment.kind == "asset"]


def test_three_pictures_at_one_offset_keep_source_occurrence_order():
    first_a, middle_b, second_a = _aba_images()
    chunks = (
        chunk(
            "body:0001",
            "1. The answer is ___ here.",
            images=(first_a, middle_b, second_a),
        ),
    )
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("The answer is "),
                    gap(),
                    text(" here."),
                    picture(first_a.asset_id),
                    picture(middle_b.asset_id),
                    picture(second_a.asset_id),
                ]
            }
        ],
        printed_label="1",
    )

    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item

    assert _built_asset_ids(result.body[0]) == [
        first_a.asset_id,
        middle_b.asset_id,
        second_a.asset_id,
    ]


def test_reply_picture_order_does_not_change_the_built_source_order():
    first_a, middle_b, second_a = _aba_images()
    chunks = (
        chunk(
            "body:0001",
            "1. The answer is ___ here.",
            images=(first_a, middle_b, second_a),
        ),
    )
    produced = item(
        chunks,
        [
            {
                "segments": [
                    text("The answer is "),
                    gap(),
                    text(" here."),
                    picture(middle_b.asset_id),
                    picture(first_a.asset_id),
                    picture(second_a.asset_id),
                ]
            }
        ],
        printed_label="1",
    )

    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item

    assert _built_asset_ids(result.body[0]) == [
        first_a.asset_id,
        middle_b.asset_id,
        second_a.asset_id,
    ]


def test_pictures_in_keeps_occurrence_order_for_equal_places():
    first_a, middle_b, second_a = _aba_images()
    provenance = ChunkProvenance()
    provenance.add(
        0,
        chunk(
            "body:0001",
            "1. The answer is ___ here.",
            images=(first_a, middle_b, second_a),
        ),
    )

    assert provenance.pictures_in(0, 30) == [
        (7, first_a.asset_id),
        (7, middle_b.asset_id),
        (7, second_a.asset_id),
    ]
