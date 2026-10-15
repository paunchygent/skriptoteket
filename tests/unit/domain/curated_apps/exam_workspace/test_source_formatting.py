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
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
    source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
    SourceFormatting,
    formatted_text,
)

pytestmark = pytest.mark.unit


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
    body = SourceFormatting((source,)).body(
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
    result = formatted_text("En rubrik\nVanlig text", SourceFormatting((heading, normal)))
    assert [p.heading_level for p in result] == [2, None]
    assert body_plain_text(result) == "En rubrik\nVanlig text"


def test_plain_teacher_repeated_word_copies_each_occurrence_marks_in_order():
    source = SourceFormatting((_source(("ord ", ("italic",)), ("ord", ("bold",))),))
    first = formatted_text("ord", source)
    second = formatted_text("ord", source)
    assert first[0].segments[0].marks == ("italic",)
    assert second[0].segments[0].marks == ("bold",)


def test_rebuilt_prompt_keeps_source_marks_and_model_gap():
    source = _source(("Skriv ordet ", ()), ("katt", ("bold",)), (" i luckan.", ("italic",)))
    result = SourceFormatting((source,)).body(
        (_paragraph(_text("Ange rätt substantiv "), NativeGapSegment(gap_id="gap_001")),),
        answers={"gap_001": ("katt",)},
    )
    assert body_plain_text(result) == "Skriv ordet [___] i luckan."
    assert result[0].segments[-1].marks == ("italic",)
    assert result[0].segments[1].kind == "gap"
    assert "katt" not in body_plain_text(result)


def test_alignment_repeated_inline_answers_cover_their_wrappers_without_facit_leak():
    source = _source(("a) snöbollarnas Svar: ", ()), ("snö (R) + boll (R) + ar (B)", ("italic",)))
    result = SourceFormatting((source,)).body(
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
        SourceFormatting((source,)).body(
            (_paragraph(_text("Ange svaret "), NativeGapSegment(gap_id="gap_001")),),
            answers={"gap_001": ("katt",)},
        )


def test_rebuild_refuses_ambiguous_paragraphs_instead_of_dropping_marks():
    sources = (_source(("Första raden", ("bold",))), _source(("Andra raden", ("italic",))))
    with pytest.raises(FormattingTransferError, match="ambiguous"):
        formatted_text("Helt ändrat språk", SourceFormatting(sources))


def test_unmarked_rewrite_preserves_model_wording_instead_of_rebuilding():
    source = SourceFormatting((_source(("Ursprunglig fråga", ())),))
    result = formatted_text("Omskriven fråga", source)
    assert body_plain_text(result) == "Omskriven fråga"
    assert source.path == "aligned"


def test_inserted_characters_never_inherit_source_marks():
    result = formatted_text(
        "Frasen stora katt", SourceFormatting((_source(("Frasen ", ()), ("katt", ("italic",))),))
    )
    assert [(s.text, s.marks) for p in result for s in p.segments] == [
        ("Frasen stora ", ()),
        ("katt", ("italic",)),
    ]


def test_wholly_omitted_marked_paragraph_is_rebuilt_not_silently_lost():
    from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
        complete_source_formatting,
    )

    chunks = (_source(("Läs frågan.", ())), _source(("Viktig fras", ("italic",))))
    source = SourceFormatting(chunks)
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
    assert result[1].segments[0].marks == ("italic",)
    assert source.path == "rebuilt"


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
    for body in (source_paragraphs((chunk,)), formatted_text(text, SourceFormatting((chunk,)))):
        assert body_plain_text(body) == text
        assert body[0].segments[0].marks == ("bold",)
        assert body[0].segments[-1].marks == ("italic",)


def test_source_review_preserves_all_marks_and_heading():
    source = _source(
        ("H", ("superscript",)), ("2", ("subscript",)), ("O", ("underline",)), heading=3
    )
    body = source_paragraphs((source,))
    assert body[0].heading_level == 3
    assert [s.marks for s in body[0].segments] == [("superscript",), ("subscript",), ("underline",)]
