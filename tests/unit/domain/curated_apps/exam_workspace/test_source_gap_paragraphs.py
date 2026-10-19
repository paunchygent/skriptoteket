"""Gap paragraphs are rebuilt from their source paragraph (TASK-SKRIPT-39-04-16).

Every case runs the real fixtures through ``aligned_native_item`` so the domain rule and
its wiring are proved together. The reply's wording in a blank-run paragraph is discarded;
only its gaps and their accepted values survive.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_gap_paragraphs import (
    GapCountMismatchError,
    blank_runs,
    source_paragraph,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    chunk as _chunk,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    gap as _gap,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    item as _item,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    projected as _projected,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    text as _text,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(s…t)", []),
        ("An … architect", [(3, 4)]),
        ("end.", []),
        ("....", [(0, 4)]),
        ("……", [(0, 2)]),
        ("______", [(0, 6)]),
        ("a…b", []),
        ("wait…", []),
        ("…done", []),
        ("...abc", []),
        ("abc...", []),
        ("x__y", [(1, 3)]),
        ("one ... two ___ three", [(12, 15)]),
    ],
)
def test_blank_runs_follow_character_class_only(text, expected):
    assert blank_runs(text) == expected


def test_source_paragraph_without_runs_is_the_trimmed_plain_source_text():
    chunks = (_chunk("body:0001", "  The important idea.  ", marks=("italic",)),)
    source = SourceFormatting(chunks, foreign=())
    paragraph = source_paragraph(
        source,
        source.paragraphs[0].start,
        source.paragraphs[0].end,
        source.paragraphs[0].heading,
    )
    (segment,) = paragraph.segments
    assert isinstance(segment, NativeTextSegment)
    assert segment.text == "The important idea."
    assert segment.marks == ("italic",)


def test_a_dropped_cue_beside_the_gap_comes_back_from_the_source():
    source = "72. We live in ______ (ett eget hus). (1 point)"
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("We live in "), _gap(), _text(".")]}],
        printed_label="72",
        points=1,
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item
    assert body_plain_text(result.body) == "We live in [___] (ett eget hus)."


def test_a_dropped_lead_clause_before_the_gap_comes_back_from_the_source():
    source = "19. The jacket looked thin. ______ (emellertid), it kept me warm."
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text(" "), _gap(), _text(" (emellertid), it kept me warm.")]}],
        printed_label="19",
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.body).startswith("The jacket looked thin. ")
    assert "19." not in body_plain_text(result.body)


def test_a_cue_after_a_gap_that_starts_the_paragraph_keeps_its_space():
    source = "8. ______ (Det här är) the only seats"
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text(" "), _gap(), _text("(Det här är) the only seats")]}],
        printed_label="8",
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item
    assert body_plain_text(result.body) == "[___] (Det här är) the only seats"


def test_a_gap_that_ends_the_paragraph_keeps_the_space_before_it():
    source = "1. The answer is ______"
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("The answer is "), _gap()]}],
        printed_label="1",
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.body) == "The answer is [___]"


def test_too_few_gaps_for_the_blank_runs_raises_a_count_mismatch():
    source = "The answer is ______ and ______."
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("The answer is "), _gap(), _text(".")]}],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())
    assert not isinstance(raised.value, FormattingTransferError)


@pytest.mark.parametrize(
    ("gaps", "blanks", "reason"),
    [
        (1, 2, "Frågan följer inte provformatet: 1 lucka men 2 tomma svarsrader."),
        (2, 1, "Frågan följer inte provformatet: 2 luckor men 1 tom svarsrad."),
        (0, 1, "Frågan följer inte provformatet: 0 luckor men 1 tom svarsrad."),
        (3, 4, "Frågan följer inte provformatet: 3 luckor men 4 tomma svarsrader."),
    ],
)
def test_the_mismatch_reason_is_swedish_and_inflected_by_each_count(gaps, blanks, reason):
    error = GapCountMismatchError(gaps, blanks)
    assert error.reason == reason
    assert str(error) == f"{gaps} gaps for {blanks} blank runs"


def test_too_many_gaps_for_the_blank_runs_raises_a_count_mismatch():
    source = "The answer is ______."
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("The answer is "), _gap(), _gap(), _text(".")]}],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())
    assert not isinstance(raised.value, FormattingTransferError)


def test_a_letter_hint_ellipsis_is_not_a_blank_run():
    source = "11. ______ (s…t) – A drug ..."
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text(" "), _gap(), _text(" (s…t) – A drug ...")]}],
        printed_label="11",
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item
    assert "(s…t)" in body_plain_text(result.body)
    assert body_plain_text(result.body).count("[___]") == 1


def test_a_dot_run_without_underscores_is_the_blank_run():
    source = "She .... to school (gå)."
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("She "), _gap(), _text(" to school (gå).")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item
    assert body_plain_text(result.body) == "She [___] to school (gå)."


def test_two_reply_paragraphs_aligned_to_one_source_paragraph_become_one():
    source = "alpha ______ beta ______ gamma"
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [
            {"segments": [_text("alpha")]},
            {
                "segments": [
                    _text(" "),
                    _gap(),
                    _text(" beta "),
                    _gap(),
                    _text(" gamma"),
                ]
            },
        ],
    )
    aligned = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())
    assert body_plain_text(aligned.item.body) == "alpha [___] beta [___] gamma"
    assert len(aligned.item.body) == 1
    assert len(aligned.chunks) == len(aligned.item.body)


def test_a_two_line_source_paragraph_builds_one_paragraph_keeping_the_line_break():
    text = "Write most or the most.\nOf these three questions, this is ______ difficult one."
    chunk = DocxChunk(
        "body:0001",
        "paragraph",
        text,
        text,
        runs=(DocxSourceRun(0, "Write most or the most.", ("italic",)),),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    chunks = (chunk,)
    produced = _item(
        chunks,
        [
            {"segments": [_text("Write most or the most.")]},
            {
                "segments": [
                    _text("Of these three questions, this is "),
                    _gap(),
                    _text(" difficult one."),
                ]
            },
        ],
    )
    aligned = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())
    assert body_plain_text(aligned.item.body) == (
        "Write most or the most.\nOf these three questions, this is [___] difficult one."
    )
    assert len(aligned.item.body) == 1
    assert len(aligned.chunks) == len(aligned.item.body)
    assert aligned.chunks == ("body:0001",)
    assert [
        segment.marks
        for segment in aligned.item.body[0].segments
        if isinstance(segment, NativeTextSegment)
    ] == [("italic",), (), ()]


def test_source_text_from_an_inline_answer_label_onward_stays_out():
    source = "Fill in: I ___ (vara) happy. Svar: was"
    chunks = (_chunk("body:0001", source),)
    produced = _item(
        chunks,
        [{"segments": [_text("Fill in: I "), _gap(), _text(" (vara) happy.")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item
    assert body_plain_text(result.body) == "Fill in: I [___] (vara) happy."
    assert "Svar:" not in body_plain_text(result.body)


def test_an_italic_source_run_in_the_gap_paragraph_keeps_its_mark():
    text = "The important word is ______."
    chunk = DocxChunk(
        "body:0001",
        "paragraph",
        text,
        text,
        runs=(
            DocxSourceRun(0, "The ", ()),
            DocxSourceRun(4, "important", ("italic",)),
            DocxSourceRun(13, " word is ______.", ()),
        ),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    chunks = (chunk,)
    produced = _item(
        chunks,
        [{"segments": [_text("The important word is "), _gap(), _text(".")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.body) == "The important word is [___]."
    marks = {
        segment.text: segment.marks
        for paragraph in result.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    }
    assert marks["important"] == ("italic",)


def test_a_free_text_item_keeps_its_reply_projection_beside_an_answer_line():
    chunks = (
        _chunk("body:0001", "Explain the process."),
        _chunk("body:0002", "________ Svar: photosynthesis"),
    )
    produced = ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "printed_label": None,
            "points": None,
            "key_source": None,
            "facit_text": None,
            "choices": [],
            "body": [{"segments": [_text("Explain the process.")]}],
        }
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    reply = (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Explain the process.", marks=()),),
        ),
    )
    assert result.body == _projected(chunks, reply)
    assert body_plain_text(result.body) == "Explain the process."


def test_a_paragraph_without_blank_runs_keeps_the_reply_projection():
    chunks = (_chunk("body:0001", "Give an example."),)
    produced = _item(
        chunks,
        [{"segments": [_text("Give an "), _gap(), _text(".")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    reply = (
        NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text="Give an ", marks=()),
                NativeGapSegment(gap_id="gap_001"),
                NativeTextSegment(text=".", marks=()),
            ),
        ),
    )
    assert result.body == _projected(chunks, reply)
    assert body_plain_text(result.body) == "Give an [___]."


def _mixed_class_row_chunks():
    text = "Wait ... | The answer is ____."
    return (
        DocxChunk(
            "body:0001",
            "table",
            text,
            text,
            runs=(DocxSourceRun(0, text, ()),),
            paragraphs=(
                DocxSourceParagraph(0, "Wait ...", None),
                DocxSourceParagraph(11, "The answer is ____.", None),
            ),
        ),
    )


def test_a_mixed_class_table_row_builds_one_underscore_blank():
    chunks = _mixed_class_row_chunks()
    produced = _item(
        chunks,
        [{"segments": [_text("Wait ... | The answer is "), _gap(), _text(".")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.body) == "Wait ... | The answer is [___]."


def test_a_mixed_class_table_row_with_two_gaps_raises_a_count_mismatch():
    chunks = _mixed_class_row_chunks()
    produced = _item(
        chunks,
        [
            {
                "segments": [
                    _text("Wait "),
                    _gap(),
                    _text(" | The answer is "),
                    _gap(),
                    _text("."),
                ]
            }
        ],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=())
    assert (raised.value.gaps, raised.value.blanks) == (2, 1)


def _dot_only_row_chunks():
    text = "Wait ... | Then ... ."
    return (
        DocxChunk(
            "body:0001",
            "table",
            text,
            text,
            runs=(DocxSourceRun(0, text, ()),),
            paragraphs=(
                DocxSourceParagraph(0, "Wait ...", None),
                DocxSourceParagraph(11, "Then ... .", None),
            ),
        ),
    )


def test_a_dot_only_table_row_keeps_two_blank_runs():
    chunks = _dot_only_row_chunks()
    produced = _item(
        chunks,
        [
            {
                "segments": [
                    _text("Wait "),
                    _gap(),
                    _text(" | Then "),
                    _gap(),
                    _text(" ."),
                ]
            }
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.body) == "Wait [___] | Then [___] ."
    short = _item(
        chunks,
        [{"segments": [_text("Wait ... | Then "), _gap(), _text(" .")]}],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(short, chunks=chunks, language="en", foreign_chunks=())
    assert (raised.value.gaps, raised.value.blanks) == (1, 2)
