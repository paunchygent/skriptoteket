"""The W10 answer-line drop survives source-format coverage and rebuild.

A real answer line is a paragraph of underscores that carries underline or bold runs.
The model-driven build drops the model's answer-line paragraph (W10), but the source side
still indexes the marked underscores. These tests call ``aligned_native_item`` with
source-backed ``DocxChunk`` records, so source-format coverage and ``rebuild_body`` run on
the same input the reviewer's probe used.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxMissingImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
    is_answer_space_paragraph,
)

pytestmark = pytest.mark.unit

_MARKINGS = [(), ("underline",), ("bold",)]


def _paragraph(*segments: ProducedSegment) -> ProducedParagraph:
    return ProducedParagraph(segments=segments)


def _text(text: str) -> ProducedSegment:
    return ProducedSegment(kind="text", text=text, accepted_values=())


def _blank(*accepted: str) -> ProducedSegment:
    return ProducedSegment(kind="gap", text=None, accepted_values=accepted)


def _item(*paragraphs: ProducedParagraph, kind=NativeExamItemKind.FREE_TEXT, facit="svar"):
    keyed = kind is not NativeExamItemKind.FREE_TEXT
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=kind,
        printed_label=None,
        body=tuple(paragraphs),
        key_source="copied" if keyed else None,
        facit_text=facit if keyed else None,
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )


def _chunk(
    anchor: str,
    text: str,
    *,
    runs: tuple[DocxSourceRun, ...] = (),
    images: tuple[DocxImage, ...] = (),
    missing: tuple[DocxMissingImage, ...] = (),
) -> DocxChunk:
    if not runs and text:
        runs = (DocxSourceRun(offset=0, text=text, marks=()),)
    paragraphs = (DocxSourceParagraph(offset=0, text=text),) if text else ()
    return DocxChunk(anchor, "paragraph", text, text, images, missing, runs, paragraphs)


def _answer_line(anchor: str, text: str, marks: tuple[str, ...]) -> DocxChunk:
    return _chunk(anchor, text, runs=(DocxSourceRun(offset=0, text=text, marks=marks),))


def _gaps(item) -> tuple[NativeGapSegment, ...]:
    return tuple(
        segment
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeGapSegment)
    )


@pytest.mark.parametrize("marks", _MARKINGS)
def test_a_marked_underscore_answer_line_never_reaches_the_body(marks) -> None:
    produced = _item(_paragraph(_text("Förklara.")), _paragraph(_text("_____")))
    chunks = (_chunk("body:0001", "Förklara."), _answer_line("body:0002", "_____", marks))

    aligned = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())

    assert body_plain_text(aligned.item.body) == "Förklara."
    assert aligned.chunks == ("body:0001",)


@pytest.mark.parametrize("marks", _MARKINGS)
def test_an_answer_line_between_real_paragraphs_keeps_their_own_anchors(marks) -> None:
    produced = _item(_paragraph(_text("Förklara.")), _paragraph(_text("Och varför?")))
    chunks = (
        _chunk("body:0001", "Förklara."),
        _answer_line("body:0002", "   ______  ", marks),
        _chunk("body:0003", "Och varför?"),
    )

    aligned = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())

    assert body_plain_text(aligned.item.body) == "Förklara.\nOch varför?"
    assert aligned.chunks == ("body:0001", "body:0003")


@pytest.mark.parametrize("marks", _MARKINGS)
@pytest.mark.parametrize("text", ["-------", ".......", "- . - ."])
def test_dash_and_dot_paragraphs_are_kept_marked_or_not(text: str, marks) -> None:
    produced = _item(_paragraph(_text(text)))
    chunks = (_answer_line("body:0001", text, marks),)

    aligned = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())

    assert body_plain_text(aligned.item.body) == text
    assert aligned.chunks == ("body:0001",)


@pytest.mark.parametrize("marks", _MARKINGS)
def test_an_underscore_paragraph_holding_a_picture_is_kept_in_place(marks) -> None:
    image = DocxImage(payload=b"picture", media_type="image/png", offset=0, marked_offset=0)
    produced = _item(
        _paragraph(
            ProducedSegment(kind="asset", text=None, accepted_values=(), asset_id=image.asset_id),
            _text("____"),
        )
    )
    chunks = (
        _chunk(
            "body:0001",
            "____",
            runs=(DocxSourceRun(offset=0, text="____", marks=marks),),
            images=(image,),
        ),
    )

    aligned = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())

    (paragraph,) = aligned.item.body
    assert paragraph.segments == (
        NativeAssetSegment(asset_id=image.asset_id),
        NativeTextSegment(text="____", marks=marks),
    )
    assert aligned.chunks == ("body:0001",)


@pytest.mark.parametrize("marks", _MARKINGS)
def test_a_standalone_underscore_gap_paragraph_keeps_its_gap(marks) -> None:
    produced = _item(_paragraph(_blank("svar")), kind=NativeExamItemKind.GAP_FILL)
    chunks = (_answer_line("body:0001", "_____", marks),)

    aligned = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())

    (paragraph,) = aligned.item.body
    assert paragraph.segments == (NativeGapSegment(gap_id="gap_001"),)
    assert _gaps(aligned.item)[0].gap_id == "gap_001"
    assert aligned.item.gaps[0].accepted_values == ("svar",)


def test_an_inline_gap_survives_a_trailing_marked_answer_line() -> None:
    produced = _item(
        _paragraph(_text("ett djur:"), _blank("katt"), _text("i rutan.")),
        kind=NativeExamItemKind.GAP_FILL,
        facit="katt",
    )
    chunks = (
        _chunk(
            "body:0001",
            "Ange ett djur: _____ i rutan.",
            runs=(
                DocxSourceRun(offset=0, text="Ange ", marks=("bold",)),
                DocxSourceRun(offset=5, text="ett djur: _____ i rutan.", marks=()),
            ),
        ),
        _answer_line("body:0002", "  _  _ ", ("underline",)),
    )

    observed: list[str] = []
    aligned = aligned_native_item(
        produced,
        chunks=chunks,
        language="sv",
        formatting_observer=observed.append,
        foreign_chunks=(),
    )

    assert observed == ["rebuilt"]
    assert body_plain_text(aligned.item.body) == "Ange ett djur: [___] i rutan."
    assert _gaps(aligned.item) == (NativeGapSegment(gap_id="gap_001"),)
    assert aligned.item.gaps[0].accepted_values == ("katt",)
    assert "body:0002" not in aligned.chunks


def test_an_unresolved_source_picture_still_raises_before_formatting() -> None:
    produced = _item(_paragraph(_text("Se bilden")))
    missing = DocxMissingImage(
        reference="word/media/image1.png", media_type="image/png", offset=0, marked_offset=0
    )
    chunks = (_chunk("body:0001", "Se bilden", missing=(missing,)),)

    with pytest.raises(ValueError, match="unresolved source pictures"):
        aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=())


def test_is_answer_line_text_needs_an_underscore() -> None:
    assert is_answer_line_text("____")
    assert is_answer_line_text("  _  _  ")
    assert is_answer_line_text("_")
    assert not is_answer_line_text("")
    assert not is_answer_line_text("   ")
    assert not is_answer_line_text("-----")
    assert not is_answer_line_text(".....")


def test_is_answer_space_paragraph_excludes_pictures() -> None:
    assert is_answer_space_paragraph("____", 0, 4, ())
    assert not is_answer_space_paragraph("____", 0, 4, (2,))
    assert not is_answer_space_paragraph("Se ____", 0, 7, ())
