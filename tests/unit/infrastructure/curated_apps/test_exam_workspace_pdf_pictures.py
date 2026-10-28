"""PDF pictures placed on the page land in their questions (TASK-SKRIPT-39-10-02)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    NO_READABLE_TEXT,
    PdfPlumberExamChunker,
    PdfPlumberLabelerMarkdown,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_picture_test_support import (
    PICTURE_SIZE,
    assert_drawing_chunk,
    pdf_chunks,
    picture_tag,
    solid_png,
    triangle_figure,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

_PICTURE_ASPECT = 3 / 2
_PICTURE_TOLERANCE = 0.05


def _assert_picture_aspect(payload: bytes) -> None:
    with Image.open(io.BytesIO(payload)) as picture:
        aspect = picture.size[0] / picture.size[1]
    assert abs(aspect - _PICTURE_ASPECT) / _PICTURE_ASPECT <= _PICTURE_TOLERANCE


def test_embedded_picture_between_questions_becomes_one_drawing_chunk_between_them() -> None:  # noqa: E501
    payload = solid_png(*PICTURE_SIZE)
    chunks = pdf_chunks(
        "<p>Fråga 1. Titta på bilden.</p>"
        f"<p>{picture_tag(payload, 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks] == [
        "Fråga 1. Titta på bilden.",
        "",
        "Fråga 2. Gå vidare.",
    ]
    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002", "body:0003"]
    _assert_picture_aspect(assert_drawing_chunk(chunks[1], anchor="body:0002"))


def test_labeler_source_carries_each_drawing_png_in_images_with_empty_markdown() -> None:
    payload = solid_png(*PICTURE_SIZE)
    content = pdf_bytes(
        "<p>Fråga 1. Titta på bilden.</p>"
        f"<p>{picture_tag(payload, 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Beskriv triangeln med hörnen.</p>"
        f"<p>{triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 3. Gå vidare.</p>"
    )

    chunks = PdfPlumberExamChunker().chunk(content=content).chunks
    source = PdfPlumberLabelerMarkdown().source(content=content)

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 2
    assert [chunk.anchor for chunk in source.chunks] == [chunk.anchor for chunk in chunks]
    for chunk in drawings:
        (image,) = chunk.images
        assert chunk.marked_text == ""
        assert source.images[chunk.anchor] == image.payload
    for chunk in source.chunks:
        if chunk.kind != "drawing":
            assert chunk.marked_text
            assert chunk.anchor not in source.images
    assert set(source.images) == {chunk.anchor for chunk in drawings}


def test_picture_only_pdf_is_a_validation_error() -> None:
    payload = solid_png(*PICTURE_SIZE)
    content = pdf_bytes(f"<p>{picture_tag(payload, 'width:120pt;height:80pt')}</p>")

    with pytest.raises(DomainError) as raised:
        PdfPlumberExamChunker().chunk(content=content).chunks

    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert raised.value.message == NO_READABLE_TEXT


def test_repeated_logo_is_dropped_while_a_body_picture_is_kept() -> None:
    logo = solid_png(60, 20, color=(200, 30, 30))
    body_picture = solid_png(*PICTURE_SIZE)
    content = pdf_bytes(
        '<div style="position: fixed; top: -50pt; left: 0">'
        f"{picture_tag(logo, 'height:24pt')}</div>"
        "<p>Fråga 1. Första sidan.</p>"
        '<p style="page-break-before: always">Fråga 2. Andra sidan.</p>'
        f"<p>{picture_tag(body_picture, 'width:120pt;height:80pt')}</p>"
        '<p style="page-break-before: always">Fråga 3. Tredje sidan.</p>'
    )

    chunks = PdfPlumberExamChunker().chunk(content=content).chunks

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "paragraph",
        "drawing",
        "paragraph",
    ]
    assert [chunk.text for chunk in chunks] == [
        "Fråga 1. Första sidan.",
        "Fråga 2. Andra sidan.",
        "",
        "Fråga 3. Tredje sidan.",
    ]
    _assert_picture_aspect(assert_drawing_chunk(chunks[2], anchor="body:0003"))


def test_large_placed_picture_stays_a_picture() -> None:
    payload = solid_png(420, 610)
    chunks = pdf_chunks(
        "<p>1. Beskriv figuren.</p>"
        f"<p>{picture_tag(payload, 'width:420pt;height:610pt')}</p>"
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    image = assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    with Image.open(io.BytesIO(image)) as shot:
        aspect = shot.size[0] / shot.size[1]
    assert abs(aspect - 420 / 610) / (420 / 610) <= 0.05
