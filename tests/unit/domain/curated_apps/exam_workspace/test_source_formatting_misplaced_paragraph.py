"""A body paragraph whose text is another question's source is rebuilt from this item's own
source paragraph, or dropped when no own paragraph is left to show (TASK-SKRIPT-39-04-15 D4).
Every other paragraph keeps the model's wording."""

from base64 import b64decode

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
)

pytestmark = pytest.mark.unit

_OWN = "8. Read the stanza: We played all day. Which term names the pattern?"
_Q7 = "7. In a poem, we hear the wind. Which term names the tired nurse?"
_REPLY = "Which term names the tired nurse?"


def _chunk(anchor: str, *runs: tuple[str, tuple[str, ...]]) -> DocxChunk:
    offset = 0
    spans = []
    for text, marks in runs:
        spans.append(DocxSourceRun(offset=offset, text=text, marks=marks))
        offset += len(text)
    text = "".join(run.text for run in spans)
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=tuple(spans),
        paragraphs=(DocxSourceParagraph(offset=0, text=text, heading_level=None),),
    )


def _text(text: str) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=())


def _paragraph(*segments: NativeSegment) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=segments)


def test_a_paragraph_repeating_another_questions_source_is_rebuilt_from_this_items_own():
    source = SourceFormatting((_chunk("own", (_OWN, ())),), ignored=("8.",), foreign=(_Q7,))

    body = source.body((_paragraph(_text(_REPLY)),))

    assert body_plain_text(body) == _OWN[3:]
    assert source.path == "rebuilt"


def test_a_paragraph_absent_from_every_other_source_keeps_the_model_wording():
    source = SourceFormatting(
        (_chunk("own", (_OWN, ())),), ignored=("8.",), foreign=("7. Helt annan fråga.",)
    )

    body = source.body((_paragraph(_text(_REPLY)),))

    assert body_plain_text(body) == _REPLY
    assert source.path == "aligned"


def test_a_paragraph_this_item_also_owns_takes_the_exact_path_unchanged():
    shared = "Välj rätt alternativ."
    source = SourceFormatting((_chunk("own", (shared, ())),), foreign=(shared, "Något annat."))

    body = source.body((_paragraph(_text(shared)),))

    assert body_plain_text(body) == shared
    assert source.path == "exact"


def test_a_reworded_paragraph_that_is_no_other_source_keeps_the_model_wording():
    own = _chunk("own", ("Förklara hur vatten blir ånga.", ()))
    source = SourceFormatting((own,), foreign=("Helt annat innehåll i en annan fråga.",))

    body = source.body((_paragraph(_text("Förklara hur ånga blir vatten.")),))

    assert body_plain_text(body) == "Förklara hur ånga blir vatten."
    assert source.path == "aligned"


def test_a_misplaced_paragraph_is_dropped_when_no_own_paragraph_is_left():
    chunks = (_chunk("p1", ("Första frågan.", ())), _chunk("p2", ("Andra frågan.", ())))
    source = SourceFormatting(chunks, foreign=("Främmande fråga.",))

    body = source.body(
        (
            _paragraph(_text("Första frågan.")),
            _paragraph(_text("Andra frågan.")),
            _paragraph(_text("Främmande fråga.")),
        )
    )

    assert body_plain_text(body) == "Första frågan.\nAndra frågan."
    assert source.path == "exact"


def test_a_misplaced_paragraph_with_a_gap_segment_is_left_to_the_alignment():
    source = SourceFormatting((_chunk("own", (_OWN, ())),), ignored=("8.",), foreign=(_Q7,))

    body = source.body((_paragraph(_text(_REPLY), NativeGapSegment(gap_id="gap_001")),))

    assert source.path == "aligned"
    assert body_plain_text(body) == f"{_REPLY}[___]"


def test_a_rebuilt_misplaced_paragraph_carries_the_source_marks():
    own = _chunk("own", ("8. Read the ", ()), ("stanza", ("bold",)), (": We played all day.", ()))
    source = SourceFormatting((own,), ignored=("8.",), foreign=(_Q7,))

    body = source.body((_paragraph(_text(_REPLY)),))

    marks = [
        (segment.text, segment.marks)
        for paragraph in body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]
    assert marks == [("Read the ", ()), ("stanza", ("bold",)), (": We played all day.", ())]
    assert source.path == "rebuilt"


def test_a_rebuilt_paragraph_drops_the_trailing_space_an_excluded_points_span_leaves():
    own = "8. Which term names the pattern? (1 point)"
    points_start = own.index("(1 point)")
    source = SourceFormatting(
        (_chunk("own", (own, ())),),
        ignored=("8.",),
        excluded=((points_start, points_start + len("(1 point)")),),
        foreign=("7. Which term names the tired nurse?",),
    )

    body = source.body((_paragraph(_text("Which term names the tired nurse?")),))

    assert body_plain_text(body) == "Which term names the pattern?"
    assert source.path == "rebuilt"


def test_a_reply_paragraph_spanning_two_foreign_chunks_is_not_misplaced():
    source = SourceFormatting(
        (_chunk("own", ("Egen fråga.", ())),),
        foreign=("First question ends here.", "Second question starts."),
    )

    body = source.body((_paragraph(_text("ends here. Second question")),))

    assert body_plain_text(body) == "ends here. Second question"
    assert source.path == "aligned"


def test_a_reply_inside_one_foreign_chunk_is_still_misplaced():
    source = SourceFormatting(
        (_chunk("own", ("Egen fråga.", ())),),
        foreign=("First question ends here.", "Second question starts."),
    )

    body = source.body((_paragraph(_text("question ends here.")),))

    assert body_plain_text(body) == "Egen fråga."
    assert source.path == "rebuilt"


def test_a_rebuilt_paragraph_shows_the_whole_stem_around_an_excluded_points_interval():
    own = "2. Describe (2 p) the rock cycle."
    points = own.index("(2 p)")
    source = SourceFormatting(
        (_chunk("own", (own, ())), _chunk("next", ("Use a diagram.", ()))),
        ignored=("2.",),
        excluded=((points, points + len("(2 p)")),),
        foreign=("1. Explain the water cycle.",),
    )

    body = source.body(
        (_paragraph(_text("Explain the water cycle.")), _paragraph(_text("Use a diagram.")))
    )

    assert body_plain_text(body) == "Describe the rock cycle.\nUse a diagram."
    assert source.path == "rebuilt"


def test_a_rebuilt_table_cell_shows_the_whole_cell_around_an_excluded_points_interval():
    cell = "2. Describe (2 p) the rock cycle. | Use a diagram."
    points = cell.index("(2 p)")
    source = SourceFormatting(
        (
            DocxChunk(
                "own",
                "table",
                cell,
                cell,
                paragraphs=(
                    DocxSourceParagraph(0, "2. Describe (2 p) the rock cycle."),
                    DocxSourceParagraph(cell.index("Use a diagram."), "Use a diagram."),
                ),
            ),
        ),
        ignored=("2.",),
        excluded=((points, points + len("(2 p)")),),
        foreign=("1. Explain the water cycle.",),
    )

    body = source.body(
        (_paragraph(_text("Explain the water cycle.")), _paragraph(_text("Use a diagram.")))
    )

    assert body_plain_text(body) == "Describe the rock cycle.\nUse a diagram."
    assert source.path == "rebuilt"


def test_a_points_interval_right_after_the_label_leaves_the_whole_stem_rebuilt():
    own = "2. (2 p) Describe the rock cycle."
    points = own.index("(2 p)")
    source = SourceFormatting(
        (_chunk("own", (own, ())), _chunk("next", ("Use a diagram.", ()))),
        ignored=("2.",),
        excluded=((points, points + len("(2 p)")),),
        foreign=("1. Explain the water cycle.",),
    )

    body = source.body((_paragraph(_text("Explain the water cycle.")),))

    assert body_plain_text(body) == "Describe the rock cycle."
    assert source.path == "rebuilt"


def test_a_rebuilt_paragraph_keeps_the_marks_around_an_excluded_points_interval():
    own = "2. The red (2 p) blue house."
    points = own.index("(2 p)")
    source = SourceFormatting(
        (
            _chunk(
                "own",
                ("2. The ", ()),
                ("red ", ("bold",)),
                ("(2 p)", ()),
                (" blue", ("bold",)),
                (" house.", ()),
            ),
        ),
        ignored=("2.",),
        excluded=((points, points + len("(2 p)")),),
        foreign=("1. Explain the water cycle.",),
    )

    body = source.body((_paragraph(_text("Explain the water cycle.")),))

    assert body_plain_text(body) == "The red blue house."
    marks = [
        (segment.text, segment.marks)
        for paragraph in body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]
    assert marks == [("The ", ()), ("red", ("bold",)), (" blue", ("bold",)), (" house.", ())]
    assert source.path == "rebuilt"


_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)


def _picture_chunk(anchor: str, text: str, offset: int) -> DocxChunk:
    image = DocxImage(payload=_PIXEL_PNG, media_type="image/png", offset=offset)
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        paragraphs=(DocxSourceParagraph(offset=0, text=text, heading_level=None),),
        images=(image,),
    )


def test_a_misplaced_paragraph_whose_own_source_holds_a_picture_raises():
    text = "2. Explain the process in this diagram."
    source = SourceFormatting(
        (_picture_chunk("own", text, text.index("process")),),
        ignored=("2.",),
        foreign=(_Q7,),
    )

    with pytest.raises(FormattingTransferError, match="picture"):
        source.body((_paragraph(_text(_REPLY)),))


def test_a_second_shared_paragraph_after_the_cursor_is_still_owned():
    shared = "Give a reason."
    source = SourceFormatting(
        (_chunk("own1", (shared, ())), _chunk("own2", ("Describe the rock cycle.", ()))),
        foreign=(shared,),
    )

    body = source.body((_paragraph(_text(shared)), _paragraph(_text(shared))))

    assert body_plain_text(body) == "Give a reason.\nGive a reason."
    assert source.path != "rebuilt"


def test_a_rebuild_skips_an_already_shown_paragraph_before_the_cursor():
    first = "Alpha first question."
    second = "Beta second question."
    source = SourceFormatting(
        (_chunk("own1", (first, ())), _chunk("own2", (second, ()))),
        foreign=(_Q7,),
    )
    source.projected.add(source.paragraphs[0].start)

    body = source.body((_paragraph(_text(_REPLY)),))

    assert body_plain_text(body) == second
    assert source.path == "rebuilt"
