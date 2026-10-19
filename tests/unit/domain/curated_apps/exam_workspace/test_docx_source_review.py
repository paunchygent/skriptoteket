"""The teacher-review fallback item drops printed answer lines (W10).

``review_source_item`` builds its body from the raw source chunks, so it must apply the
same printed-answer-line rule as the model-driven build: a paragraph made only of
whitespace and underscores is answer space, never question text. Dashes, dots and every
paragraph that carries a picture stay.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    aligned_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import (
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit

_REASON = "Kontrollera frågan manuellt."


def _chunk(
    anchor: str,
    text: str,
    images: tuple[DocxImage, ...] = (),
) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text, images)


def _image(offset: int = 0) -> DocxImage:
    return DocxImage(
        payload=b"picture", media_type="image/png", offset=offset, marked_offset=offset
    )


def test_review_source_item_drops_printed_answer_lines_and_keeps_dashes() -> None:
    chunks = (
        _chunk("body:0001", "Förklara."),
        _chunk("body:0002", "______"),
        _chunk("body:0003", "  __ _ "),
        _chunk("body:0004", "-----"),
    )

    item = review_source_item(chunks, _REASON)

    assert body_text_lines(item.body) == ("Förklara.", "-----")
    assert [paragraph.segments for paragraph in item.body] == [
        (NativeTextSegment(text="Förklara.", marks=()),),
        (NativeTextSegment(text="-----", marks=()),),
    ]


def test_review_source_item_of_only_printed_answer_lines_uses_the_empty_placeholder() -> None:
    chunks = (
        _chunk("body:0001", "____"),
        _chunk("body:0002", "  _  _ "),
    )

    item = review_source_item(chunks, _REASON)

    assert item.body == (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Tomt källstycke.", marks=()),),
        ),
    )


def test_review_source_item_keeps_a_picture_paragraph() -> None:
    image = _image()
    chunks = (_chunk("body:0001", "Se bilden", (image,)),)

    item = review_source_item(chunks, _REASON)

    assert item.body[0].segments == (
        NativeAssetSegment(asset_id=image.asset_id),
        NativeTextSegment(text="Se bilden", marks=()),
    )


def test_review_source_item_keeps_an_underscore_paragraph_that_carries_a_picture() -> None:
    image = _image()
    chunks = (_chunk("body:0001", "____", (image,)),)

    item = review_source_item(chunks, _REASON)

    assert NativeAssetSegment(asset_id=image.asset_id) in item.body[0].segments
    assert body_text_lines(item.body) == ("____",)


def test_review_source_item_alignment_drops_the_anchors_of_printed_answer_lines() -> None:
    chunks = (
        _chunk("body:0001", "Förklara."),
        _chunk("body:0002", "______"),
        _chunk("body:0003", "-----"),
    )

    aligned = aligned_source_item(review_source_item(chunks, _REASON), chunks)

    assert aligned.chunks == ("body:0001", "body:0003")
    assert aligned.shows("body:0001")
    assert not aligned.shows("body:0002")


def test_review_source_item_alignment_of_only_printed_answer_lines_is_unaligned() -> None:
    chunks = (
        _chunk("body:0001", "____"),
        _chunk("body:0002", "  _  _ "),
    )

    aligned = aligned_source_item(review_source_item(chunks, _REASON), chunks)

    assert aligned.chunks == (None,)
    assert len(aligned.item.body) == 1


def test_review_source_item_alignment_keeps_a_picture_between_dropped_lines() -> None:
    image = _image()
    chunks = (
        _chunk("body:0001", "Förklara."),
        _chunk("body:0002", "Se bilden", (image,)),
        _chunk("body:0003", "______"),
        _chunk("body:0004", "-----"),
    )

    aligned = aligned_source_item(review_source_item(chunks, _REASON), chunks)

    assert aligned.chunks == ("body:0001", "body:0002", "body:0004")
    assert body_text_lines(aligned.item.body) == ("Förklara.", "Se bilden", "-----")
