"""Source typography is copied by code, including reconstruction and refusal."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
    source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
    SourceFormatting,
    formatted_text,
)

pytestmark = pytest.mark.unit


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


def _source(*runs: tuple[str, tuple[str, ...]], heading: int | None = None) -> DocxChunk:
    offset = 0
    spans = []
    for text, marks in runs:
        spans.append(DocxSourceRun(offset=offset, text=text, marks=marks))
        offset += len(text)
    text = "".join(run.text for run in spans)
    return DocxChunk(
        "p1",
        "paragraph",
        text,
        text,
        runs=tuple(spans),
        paragraphs=(DocxSourceParagraph(offset=0, text=text, heading_level=heading),),
    )


def _paragraph(*segments):
    return NativeParagraph(heading_level=None, segments=segments)


def _text(text):
    return NativeTextSegment(text=text, marks=())


def test_copy_marks_splits_source_runs_and_keeps_spacing_around_gap():
    source = _source(("Frasen ", ()), ("tre korta svar", ("italic",)), (" är en NF.", ()))
    body = SourceFormatting((source,), foreign=()).body(
        (
            _paragraph(
                _text("Frasen tre korta svar är en "),
                NativeGapSegment(gap_id="gap_001"),
                _text("."),
            ),
        )
    )
    assert body_plain_text(body) == "Frasen tre korta svar är en [___]."
    assert [(s.text, s.marks) for p in body for s in p.segments if s.kind == "text"] == [
        ("Frasen ", ()),
        ("tre korta svar", ("italic",)),
        (" är en ", ()),
        (".", ()),
    ]
    assert "NF" not in body_plain_text(body)


def test_text_across_source_paragraphs_keeps_each_heading_level():
    heading = _source(("En rubrik", ("bold",)), heading=2)
    normal = _source(("Vanlig text", ()))
    result = formatted_text(
        "En rubrik\nVanlig text", SourceFormatting((heading, normal), foreign=())
    )
    assert [p.heading_level for p in result] == [2, None]
    assert body_plain_text(result) == "En rubrik\nVanlig text"


def test_plain_teacher_repeated_word_copies_each_occurrence_marks_in_order():
    source = SourceFormatting((_source(("ord ", ("italic",)), ("ord", ("bold",))),), foreign=())
    first = formatted_text("ord", source)
    second = formatted_text("ord", source)
    assert _as_text(first[0].segments[0]).marks == ("italic",)
    assert _as_text(second[0].segments[0]).marks == ("bold",)


def test_rebuilt_prompt_keeps_source_marks_and_model_gap():
    source = _source(("Skriv ordet ", ()), ("katt", ("bold",)), (" i luckan.", ("italic",)))
    result = SourceFormatting((source,), foreign=()).body(
        (_paragraph(_text("Ange rätt substantiv "), NativeGapSegment(gap_id="gap_001")),),
        answers={"gap_001": ("katt",)},
    )
    assert body_plain_text(result) == "Skriv ordet [___] i luckan."
    assert _as_text(result[0].segments[-1]).marks == ("italic",)
    assert result[0].segments[1].kind == "gap"
    assert "katt" not in body_plain_text(result)


def test_alignment_repeated_inline_answers_cover_their_wrappers_without_facit_leak():
    source = _source(("a) snöbollarnas Svar: ", ()), ("snö (R) + boll (R) + ar (B)", ("italic",)))
    result = SourceFormatting((source,), foreign=()).body(
        (
            _paragraph(
                _text("a) snö + boll + ar"),
                *(NativeGapSegment(gap_id=f"gap_{i:03d}") for i in range(1, 4)),
            ),
        ),
        answers={"gap_001": ("R",), "gap_002": ("R",), "gap_003": ("B",)},
    )
    assert body_plain_text(result) == "a) snö + boll + ar[___][___][___]"
    italic = "".join(
        s.text for p in result for s in p.segments if s.kind == "text" and "italic" in s.marks
    )
    assert "snö + boll + ar" in italic
    assert "Svar:" not in body_plain_text(result)


def test_rebuild_refuses_gap_without_unique_source_position():
    source = _source(("Skriv katt eller katt.", ("underline",)))
    with pytest.raises(FormattingTransferError, match="unique source location"):
        SourceFormatting((source,), foreign=()).body(
            (_paragraph(_text("Ange svaret "), NativeGapSegment(gap_id="gap_001")),),
            answers={"gap_001": ("katt",)},
        )


def test_rebuild_refuses_ambiguous_paragraphs_instead_of_dropping_marks():
    sources = (_source(("Första raden", ("bold",))), _source(("Andra raden", ("italic",))))
    with pytest.raises(FormattingTransferError, match="ambiguous"):
        formatted_text("Helt ändrat språk", SourceFormatting(sources, foreign=()))


def test_unmarked_rewrite_preserves_model_wording_instead_of_rebuilding():
    source = SourceFormatting((_source(("Ursprunglig fråga", ())),), foreign=())
    result = formatted_text("Omskriven fråga", source)
    assert body_plain_text(result) == "Omskriven fråga"
    assert source.path == "aligned"


def test_inserted_characters_never_inherit_source_marks():
    result = formatted_text(
        "Frasen stora katt",
        SourceFormatting((_source(("Frasen ", ()), ("katt", ("italic",))),), foreign=()),
    )
    assert [(_as_text(s).text, _as_text(s).marks) for p in result for s in p.segments] == [
        ("Frasen stora ", ()),
        ("katt", ("italic",)),
    ]


def test_wholly_omitted_marked_paragraph_is_rebuilt_not_silently_lost():
    chunks = (_source(("Läs frågan.", ())), _source(("Viktig fras", ("italic",))))
    source = SourceFormatting(chunks, foreign=())
    body = formatted_text("Läs frågan.", source)
    result = complete_source_formatting(
        chunks,
        (source,),
        source,
        body,
        printed_label=None,
        answers={},
        can_rebuild_body=True,
    )
    assert body_plain_text(result) == "Läs frågan.\nViktig fras"
    assert _as_text(result[1].segments[0]).marks == ("italic",)
    assert source.path == "rebuilt"


@pytest.mark.parametrize("label", ["Correct answer:", "Correct answers:", "Svar:", "Facit:"])
def test_an_omitted_facit_paragraph_is_never_rebuilt_into_the_body(label):
    # Live Diagnostic 85 2026-10-16: an omitted "Correct answer:" line was rebuilt as text.
    chunks = (_source(("Läs frågan.", ())), _source((f"{label} ", ()), ("svaret", ("italic",))))
    source = SourceFormatting(chunks, foreign=())
    body = formatted_text("Läs frågan.", source)
    with pytest.raises(FormattingTransferError, match="expose facit wording"):
        complete_source_formatting(
            chunks,
            (source,),
            source,
            body,
            printed_label=None,
            answers={},
            can_rebuild_body=True,
        )


def test_flattened_table_rows_keep_separators_and_each_cell_mark():
    text = "a | b\nc | d"
    chunk = DocxChunk(
        "table1",
        "table",
        text,
        text,
        runs=(DocxSourceRun(0, "a", ("bold",)), DocxSourceRun(4, "b", ("italic",))),
        paragraphs=tuple(
            DocxSourceParagraph(offset, value, None)
            for offset, value in ((0, "a"), (4, "b"), (6, "c"), (10, "d"))
        ),
    )
    for body in (
        source_paragraphs((chunk,)),
        formatted_text(text, SourceFormatting((chunk,), foreign=())),
    ):
        assert body_plain_text(body) == text
        assert _as_text(body[0].segments[0]).marks == ("bold",)
        assert _as_text(body[0].segments[-1]).marks == ("italic",)


def test_source_review_preserves_all_marks_and_heading():
    source = _source(
        ("H", ("superscript",)), ("2", ("subscript",)), ("O", ("underline",)), heading=3
    )
    body = source_paragraphs((source,))
    assert body[0].heading_level == 3
    assert [_as_text(s).marks for s in body[0].segments] == [
        ("superscript",),
        ("subscript",),
        ("underline",),
    ]


def test_rebuilt_paragraph_drops_the_printed_label_native_field_already_carries():
    text = "1. Identify the important concept."
    chunk = _source((text, ("bold",)))
    source = SourceFormatting((chunk,), ignored=("1",), foreign=())
    body = formatted_text("Describe the important concept.", source)
    result = complete_source_formatting(
        (chunk,), (source,), source, body, printed_label="1", answers={}, can_rebuild_body=True
    )
    assert body_plain_text(result) == "Identify the important concept."
    assert _as_text(result[0].segments[0]).marks == ("bold",)


def test_omitted_size_heading_paragraph_is_rebuilt_with_its_level():
    heading = _source(("Läs det här avsnittet noga.", ()), heading=2)
    question = _source(("Svara på frågan.", ()))
    source = SourceFormatting((heading, question), foreign=())
    body = formatted_text("Svara på frågan.", source)
    result = complete_source_formatting(
        (heading, question),
        (source,),
        source,
        body,
        printed_label=None,
        answers={},
        can_rebuild_body=True,
    )
    assert body_plain_text(result) == "Läs det här avsnittet noga.\nSvara på frågan."
    assert [paragraph.heading_level for paragraph in result] == [2, None]
    assert source.path == "rebuilt"


def test_rewritten_unmarked_heading_keeps_model_wording_and_source_level():
    heading = _source(("Viktig rubrik", ()), heading=2)
    source = SourceFormatting((heading,), foreign=())
    result = formatted_text("Ny rubrik", source)
    assert body_plain_text(result) == "Ny rubrik"
    assert result[0].heading_level == 2
    assert source.path == "aligned"


def test_omitted_table_heading_paragraph_is_rebuilt_with_its_level():
    text = "Rubrikcell | Svarstext"
    table = DocxChunk(
        "table1",
        "table",
        text,
        text,
        runs=(),
        paragraphs=(
            DocxSourceParagraph(0, "Rubrikcell", 2),
            DocxSourceParagraph(13, "Svarstext", None),
        ),
    )
    source = SourceFormatting((table,), foreign=())
    body = formatted_text("Svarstext", source)
    result = complete_source_formatting(
        (table,), (source,), source, body, printed_label=None, answers={}, can_rebuild_body=True
    )
    assert [paragraph.heading_level for paragraph in result] == [2, None]
    assert body_plain_text(result) == "Rubrikcell\nSvarstext"
    assert source.path == "rebuilt"


def test_omitted_marked_word_before_free_text_body_is_rebuilt_from_source():
    safety = _source(("Safety.", ("bold",)), (" Do not mix acids.", ()))
    source = SourceFormatting((safety,), foreign=())
    body = formatted_text("Do not mix acids.", source)
    result = complete_source_formatting(
        (safety,), (source,), source, body, printed_label=None, answers={}, can_rebuild_body=True
    )
    assert body_plain_text(result) == "Safety. Do not mix acids."
    assert _as_text(result[0].segments[0]).text == "Safety."
    assert _as_text(result[0].segments[0]).marks == ("bold",)
    assert source.path == "rebuilt"


def test_marked_choice_labels_are_exempt_through_their_native_ordinals():
    from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
        NativeSourceEntry,
    )

    text = "Which city?\na) Paris\nb) Lyon"
    chunk = DocxChunk(
        "body:0001",
        "paragraph",
        text,
        text,
        runs=(
            DocxSourceRun(12, "a) ", ("bold",)),
            DocxSourceRun(15, "Paris", ()),
            DocxSourceRun(21, "b) ", ("bold",)),
            DocxSourceRun(24, "Lyon", ()),
        ),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    body_source = SourceFormatting((chunk,), foreign=())
    choice_source = SourceFormatting((chunk,), foreign=())
    body = formatted_text("Which city?", body_source)
    choices = (formatted_text("Paris", choice_source), formatted_text("Lyon", choice_source))
    assert choice_source.entry_spans == [(15, 20), (24, 28)]
    entries = (
        NativeSourceEntry("choices", 1, 15, 20),
        NativeSourceEntry("choices", 2, 24, 28),
    )
    result = complete_source_formatting(
        (chunk,),
        (body_source, choice_source),
        body_source,
        body,
        printed_label=None,
        answers={},
        can_rebuild_body=False,
        entries=entries,
    )
    assert body_plain_text(result) == "Which city?"
    assert body_plain_text(choices[0]) == "Paris"
    assert body_plain_text(choices[1]) == "Lyon"
    assert body_source.path == "exact" and choice_source.path == "exact"


def test_ordinal_labels_extend_beyond_z_and_the_roman_numeral_cap():
    from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
        NativeSourceEntry,
    )

    text = "Which city?\nAA) Paris\nMM) Lyon"
    chunk = DocxChunk(
        "body:0001",
        "paragraph",
        text,
        text,
        runs=(
            DocxSourceRun(12, "AA) ", ("bold",)),
            DocxSourceRun(16, "Paris", ()),
            DocxSourceRun(22, "MM) ", ("bold",)),
            DocxSourceRun(26, "Lyon", ()),
        ),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    body_source = SourceFormatting((chunk,), foreign=())
    choice_source = SourceFormatting((chunk,), foreign=())
    body = formatted_text("Which city?", body_source)
    formatted_text("Paris", choice_source)
    formatted_text("Lyon", choice_source)
    entries = (
        NativeSourceEntry("choices", 27, 16, 21),
        NativeSourceEntry("choices", 2000, 26, 30),
    )
    result = complete_source_formatting(
        (chunk,),
        (body_source, choice_source),
        body_source,
        body,
        printed_label=None,
        answers={},
        can_rebuild_body=False,
        entries=entries,
    )
    assert body_plain_text(result) == "Which city?"


def test_heading_projected_by_an_entry_surface_is_already_accounted():
    from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
        NativeSourceEntry,
    )

    text = "Fråga? | a) Rubrik"
    table = DocxChunk(
        "table1",
        "table",
        text,
        text,
        runs=(DocxSourceRun(9, "a) ", ("bold",)), DocxSourceRun(12, "Rubrik", ())),
        paragraphs=(
            DocxSourceParagraph(0, "Fråga?", None),
            DocxSourceParagraph(9, "a) Rubrik", 2),
        ),
    )
    body_source = SourceFormatting((table,), foreign=())
    choice_source = SourceFormatting((table,), foreign=())
    body = formatted_text("Fråga?", body_source)
    formatted_text("Rubrik", choice_source)
    entries = (NativeSourceEntry("choices", 1, 12, 18),)
    result = complete_source_formatting(
        (table,),
        (body_source, choice_source),
        body_source,
        body,
        printed_label=None,
        answers={},
        can_rebuild_body=False,
        entries=entries,
    )
    assert body_plain_text(result) == "Fråga?"
    assert choice_source.projected == {9}
