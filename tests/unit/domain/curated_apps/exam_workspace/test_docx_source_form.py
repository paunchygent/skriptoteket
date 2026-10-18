"""A chunk's source form carries the item's gaps at their source locations (TASK-SKRIPT-39-04-13).

Each case pairs source formatting a naive splice would break with the gap placement the
response contract requires: every gap once, marks and pictures where the source prints them.
"""

from base64 import b64decode

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_form import source_form
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)

_GAP = NativeGapSegment(gap_id="gap_001")
_SECOND = NativeGapSegment(gap_id="gap_002")


def _shown(*gaps: NativeGapSegment) -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Svar: ", marks=()), *gaps),
        ),
    )


def _plain(paragraph: NativeParagraph) -> list[object]:
    return [
        (segment.text, segment.marks)
        if isinstance(segment, NativeTextSegment)
        else segment.gap_id
        if isinstance(segment, NativeGapSegment)
        else segment.asset_id
        for segment in paragraph.segments
    ]


def test_a_gap_over_a_mark_boundary_keeps_the_marks_on_either_side() -> None:
    text = "Huvudstaden ___ ligger vid havet."
    chunk = DocxChunk(
        "body:0002",
        "paragraph",
        text,
        text,
        runs=(DocxSourceRun(0, "Huvudstaden __", ("bold",)),),
    )

    (paragraph,) = source_form(chunk, _shown(_GAP), {}) or ()

    assert _plain(paragraph) == [
        ("Huvudstaden ", ("bold",)),
        "gap_001",
        (" ligger vid havet.", ()),
    ]


def test_a_gap_keeps_the_picture_at_its_source_place() -> None:
    text = "Se kartan och skriv ___."
    picture = DocxImage(
        b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jJ1kAAAAASUVORK5CYII="
        ),
        "image/png",
        offset=len("Se kartan"),
        marked_offset=len("Se kartan"),
    )
    chunk = DocxChunk("body:0002", "paragraph", text, text, (picture,))

    (paragraph,) = source_form(chunk, _shown(_GAP), {}) or ()

    assert _plain(paragraph) == [
        ("Se kartan", ()),
        picture.asset_id,
        (" och skriv ", ()),
        "gap_001",
        (".", ()),
    ]
    assert isinstance(paragraph.segments[1], NativeAssetSegment)


def test_a_gap_located_by_its_answer_replaces_the_answer_text() -> None:
    text = "Sveriges huvudstad är Stockholm."
    chunk = DocxChunk("body:0002", "paragraph", text, text)

    (paragraph,) = source_form(chunk, _shown(_GAP), {"gap_001": ("Stockholm",)}) or ()

    assert _plain(paragraph) == [("Sveriges huvudstad är ", ()), "gap_001", (".", ())]


def test_two_gaps_over_one_blank_have_no_source_form() -> None:
    text = "Skriv ___ här."
    chunk = DocxChunk("body:0002", "paragraph", text, text)

    assert source_form(chunk, _shown(_GAP, _SECOND), {}) is None


def test_a_chunk_without_gaps_is_its_plain_source_rendering() -> None:
    text = "Läs noga."
    chunk = DocxChunk("body:0002", "paragraph", text, text)

    (paragraph,) = source_form(chunk, (), {}) or ()

    assert _plain(paragraph) == [("Läs noga.", ())]
