"""Each emitted body paragraph names the chunk it was projected from (TASK-SKRIPT-39-04-13 D9).

Section placement and the context and heading join replace a paragraph by its chunk's
source form, so an anchor that names a chunk the paragraph does not hold deletes content.
Each case is a reply paragraph whose output ordinal and source span disagree.
"""

from base64 import b64decode

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import paragraph_chunks
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

_PICTURE = DocxImage(
    b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jJ1kAAAAASUVORK5CYII="
    ),
    "image/png",
)


def _chunk(anchor: str, text: str, picture: bool = False) -> DocxChunk:
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        (_PICTURE,) if picture else (),
        paragraphs=(DocxSourceParagraph(0, text),) if text else (),
    )


def _text(text: str) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=())


def _project(chunks: tuple[DocxChunk, ...], *segments: NativeSegment) -> tuple[str | None, ...]:
    source = SourceFormatting(chunks, foreign=())
    source.body((NativeParagraph(heading_level=None, segments=segments),))
    return paragraph_chunks(source)


def test_text_after_an_omitted_caption_names_its_own_chunk() -> None:
    chunks = (
        _chunk("body:0001", "1. Undersök bilden."),
        _chunk("body:0002", "Se bilden.", picture=True),
        _chunk("body:0003", "Vilket djur visas?"),
    )

    anchors = _project(
        chunks,
        _text("1. Undersök bilden. "),
        NativeAssetSegment(asset_id=_PICTURE.asset_id),
        _text("Vilket djur visas?"),
    )

    assert anchors == ("body:0001", "body:0002", "body:0003")


def test_text_skipping_an_omitted_paragraph_names_the_chunk_it_was_found_in() -> None:
    chunks = (
        _chunk("body:0001", "Läs texten."),
        _chunk("body:0002", "Läs först hela texten."),
        _chunk("body:0003", "Skriv ditt svar."),
    )

    # Two exact pieces of one reply paragraph; the omitted middle paragraph lies inside the
    # projected span, so the second piece's ordinal would name it.
    anchors = _project(chunks, _text("Läs texten. "), _text("Skriv ditt svar."))

    assert anchors == ("body:0001", "body:0003")


def test_a_picture_only_chunk_between_two_texts_stands_alone() -> None:
    chunks = (
        _chunk("body:0001", "Titta här:"),
        _chunk("body:0002", "", picture=True),
        _chunk("body:0003", "Vad ser du?"),
    )

    anchors = _project(
        chunks,
        _text("Titta här: "),
        NativeAssetSegment(asset_id=_PICTURE.asset_id),
        _text("Vad ser du?"),
    )

    assert anchors == ("body:0001", "body:0002", "body:0003")
