"""The PDF import reader turns a text PDF into the Word chunker's chunk sequence."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import is_answer_line_chunk
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
    PdfPlumberLabelerMarkdown,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

_LONG = (
    "Read the text below and answer the questions. This sentence is long enough that it "
    "wraps across at least two lines in the body column of an A4 page, so the wrapped "
    "lines must join into one paragraph."
)


def _chunks(body: str, *, css: str = "") -> tuple[DocxChunk, ...]:
    return PdfPlumberExamChunker().chunk(content=pdf_bytes(body, css=css))


def _texts(chunks: tuple[DocxChunk, ...]) -> list[str]:
    return [chunk.text for chunk in chunks]


def test_wrapped_lines_join_into_one_paragraph_and_paragraphs_stay_apart() -> None:
    chunks = _chunks(f"<p>1. {_LONG}</p><p>2. Kort fråga?</p>")

    assert _texts(chunks) == [f"1. {_LONG}", "2. Kort fråga?"]
    assert [chunk.kind for chunk in chunks] == ["paragraph", "paragraph"]
    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002"]
    assert chunks[0].paragraphs[0].text == f"1. {_LONG}"
    assert chunks[0].paragraphs[0].heading_level is None


def test_soft_line_break_stays_inside_its_paragraph() -> None:
    chunks = _chunks(
        f"<p>1. {_LONG}</p><p>Choose one.</p><p>A. deep<br>B. strange<br>C. dignified</p>"
        "<p>Correct answer: A. deep</p><p>2. Next question.</p>"
    )

    assert _texts(chunks) == [
        f"1. {_LONG}",
        "Choose one.",
        "A. deep\nB. strange\nC. dignified",
        "Correct answer: A. deep",
        "2. Next question.",
    ]


def test_larger_text_becomes_headings_ranked_by_size() -> None:
    chunks = _chunks(f"<h1>Unit test kapitel 1</h1><h2>Del A: Läsförståelse</h2><p>1. {_LONG}</p>")

    assert [(chunk.kind, chunk.text) for chunk in chunks] == [
        ("heading", "Unit test kapitel 1"),
        ("heading", "Del A: Läsförståelse"),
        ("paragraph", f"1. {_LONG}"),
    ]
    assert [chunk.paragraphs[0].heading_level for chunk in chunks] == [1, 2, None]


def test_italic_is_the_marked_facit_cue_and_bold_is_a_run_mark() -> None:
    (chunk,) = _chunks("<p>Correct answer: <i>the dog barked</i> and <b>loudly</b>.</p>")

    assert chunk.text == "Correct answer: the dog barked and loudly."
    assert chunk.marked_text == "Correct answer: <i>the dog barked</i> and loudly."
    marked = {run.text.strip(): run.marks for run in chunk.runs if run.marks}
    assert marked == {"the dog barked": ("italic",), "loudly": ("bold",)}
    for run in chunk.runs:
        assert chunk.text[run.offset : run.offset + len(run.text)] == run.text


def test_ruled_table_is_one_table_chunk_with_cell_paragraphs() -> None:
    chunks = _chunks(
        "<p>Före tabellen.</p>"
        "<table><tr><td>Word</td><td>Meaning</td></tr>"
        "<tr><td>happy</td><td><b>glad</b> och lycklig</td></tr></table>"
        "<p>Efter tabellen.</p>",
        css="table { border-collapse: collapse; } td { border: 1px solid black; padding: 4pt; }",
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "table", "paragraph"]
    table = chunks[1]
    assert table.text == "Word | Meaning\nhappy | glad och lycklig"
    assert [paragraph.text for paragraph in table.paragraphs] == [
        "Word",
        "Meaning",
        "happy",
        "glad och lycklig",
    ]
    for paragraph in table.paragraphs:
        assert table.text[paragraph.offset : paragraph.offset + len(paragraph.text)] == (
            paragraph.text
        )


def test_borderless_table_keeps_a_wrapped_cell_in_its_cell() -> None:
    chunks = _chunks(
        "<p>Match the words.</p>"
        "<table><tr><td>1. respect</td><td>A. to admire someone deeply because of their "
        "abilities, qualities or achievements in life</td></tr>"
        "<tr><td>2. disdain</td><td>B. the feeling that someone is not worth any "
        "consideration</td></tr></table>",
        css="td { padding: 2pt 18pt 2pt 0; vertical-align: top; } td:first-child { width: 4cm; }",
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "table"]
    assert chunks[1].text == (
        "1. respect | A. to admire someone deeply because of their abilities, qualities or "
        "achievements in life\n2. disdain | B. the feeling that someone is not worth any "
        "consideration"
    )


def test_repeated_header_footer_and_page_numbers_are_dropped() -> None:
    pages = "".join(
        f'<p style="page-break-before: always">Fråga {page}. Svara på frågan.</p>'
        for page in range(2, 5)
    )
    chunks = _chunks(
        "<p>Namn: Endast på första sidan</p><p>Fråga 1. Svara på frågan.</p>" + pages,
        css=(
            '@page { @top-center { content: "Engelska 1 – Provet HT26"; font-size: 9pt; }'
            ' @bottom-center { content: "Sida " counter(page) " av " counter(pages);'
            " font-size: 9pt; } }"
        ),
    )

    assert _texts(chunks) == [
        "Namn: Endast på första sidan",
        "Fråga 1. Svara på frågan.",
        "Fråga 2. Svara på frågan.",
        "Fråga 3. Svara på frågan.",
        "Fråga 4. Svara på frågan.",
    ]


def test_a_bottom_line_that_does_not_repeat_is_kept() -> None:
    chunks = _chunks(
        '<p>Fråga 1. Skriv ditt svar.</p><p style="position: absolute; bottom: 0">Svar: ja</p>'
        '<p style="page-break-before: always">Fråga 2. Skriv ditt svar.</p>'
    )

    assert "Svar: ja" in _texts(chunks)


@pytest.mark.parametrize(
    "ending",
    [" och förklara resonemanget.", ""],
    ids=["mention-in-middle", "mention-at-end"],
)
def test_questions_that_name_a_page_are_not_page_furniture(ending: str) -> None:
    body = "".join(
        f'<section style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"<p>{page}. Läs sida {10 + page}{ending}</p>"
        f"<p>Unik svarstext för uppgift {page}.</p></section>"
        for page in range(1, 4)
    )
    chunks = _chunks(body, css="body { margin: 0; }")

    assert _texts(chunks) == [
        text
        for page in range(1, 4)
        for text in (
            f"{page}. Läs sida {10 + page}{ending}",
            f"Unik svarstext för uppgift {page}.",
        )
    ]


def test_a_footer_that_names_its_page_is_dropped_and_keeps_its_fixed_numbers() -> None:
    body = "".join(
        f'<p style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"Fråga {page}. Svara på frågan.</p>"
        for page in range(1, 4)
    )
    chunks = _chunks(
        body,
        css='@page { @bottom-center { content: "Engelska 1 HT26, sida " counter(page)'
        ' " av " counter(pages); font-size: 9pt; } }',
    )

    assert _texts(chunks) == [f"Fråga {page}. Svara på frågan." for page in range(1, 4)]


def test_unnumbered_prompts_that_name_a_page_are_kept() -> None:
    body = "".join(
        f'<section style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"<p>Beskriv huvudpersonens val på sida {10 + page}</p>"
        f"<p>Unik svarstext för uppgift {page}.</p></section>"
        for page in range(1, 4)
    )
    chunks = _chunks(body, css="body { margin: 0; }")

    assert _texts(chunks) == [
        text
        for page in range(1, 4)
        for text in (
            f"Beskriv huvudpersonens val på sida {10 + page}",
            f"Unik svarstext för uppgift {page}.",
        )
    ]


def test_a_footer_with_text_after_its_page_counter_is_dropped() -> None:
    body = "".join(
        f'<p style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"Fråga {page}. Svara på frågan.</p>"
        for page in range(1, 4)
    )
    chunks = _chunks(
        body,
        css='@page { @bottom-center { content: "Engelska 1, sida " counter(page)'
        ' " av " counter(pages) " – HT26"; font-size: 9pt; } }',
    )

    assert _texts(chunks) == [f"Fråga {page}. Svara på frågan." for page in range(1, 4)]


@pytest.mark.parametrize("margin", ["", "body { margin: 0; }"], ids=["page-margin", "no-margin"])
def test_a_question_numbered_like_its_page_at_body_size_is_kept(margin: str) -> None:
    body = "".join(
        f'<section style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"<p>Uppgift {page}</p><p>Beskriv ett val som huvudpersonen gör.</p></section>"
        for page in range(1, 4)
    )
    chunks = _chunks(
        body,
        css=margin + '@page { @bottom-center { content: "Sida " counter(page) " av "'
        ' counter(pages) " – Engelska 1"; font-size: 9pt; } }',
    )

    assert _texts(chunks) == [
        text
        for page in range(1, 4)
        for text in (f"Uppgift {page}", "Beskriv ett val som huvudpersonen gör.")
    ]


def test_a_body_size_header_set_off_from_the_body_is_dropped() -> None:
    body = "".join(
        f'<p style="page-break-before: {"auto" if page == 1 else "always"}">'
        f"Fråga {10 + page}. Svara på frågan.</p>"
        for page in range(1, 4)
    )
    chunks = _chunks(
        body,
        css='@page { @top-left { content: "Engelska 1 – sida " counter(page); font-size: 11pt; } }',
    )

    assert _texts(chunks) == [f"Fråga {10 + page}. Svara på frågan." for page in range(1, 4)]


def test_two_columns_read_left_column_then_right_after_the_full_width_heading() -> None:
    paragraphs = "".join(
        f"<p>Kolumnstycke {index} med lite text som fyller ut kolumnen ordentligt.</p>"
        for index in range(1, 21)
    )
    chunks = _chunks(
        f'<h1>Ordlista</h1><div class="cols">{paragraphs}</div><p>{_LONG}</p>',
        css=".cols { column-count: 2; column-gap: 1cm; }",
    )

    assert _texts(chunks) == [
        "Ordlista",
        *(
            f"Kolumnstycke {index} med lite text som fyller ut kolumnen ordentligt."
            for index in range(1, 21)
        ),
        _LONG,
    ]


def test_right_aligned_points_do_not_split_the_page_into_columns() -> None:
    questions = "".join(
        f'<p>{index}. Förklara begreppet nummer {index} kort.<span style="float: right">'
        "(2p)</span></p>"
        for index in range(1, 9)
    )
    chunks = _chunks(questions)

    assert _texts(chunks) == [
        f"{index}. Förklara begreppet nummer {index} kort. (2p)" for index in range(1, 9)
    ]


def test_drawn_underscore_lines_are_their_own_answer_line_chunks() -> None:
    chunks = _chunks(
        "<p>1. Vad heter huvudpersonen?</p>"
        "<p>__________________________________________________</p>"
        "<p>__________________________________________________</p>"
        '<div style="border-bottom: 1px solid black; height: 18pt"></div>'
        "<p>2. Nästa fråga.</p>"
    )

    assert [is_answer_line_chunk(chunk) for chunk in chunks] == [False, True, True, False]
    assert _texts(chunks)[0] == "1. Vad heter huvudpersonen?"
    assert _texts(chunks)[-1] == "2. Nästa fråga."


def test_bullet_glyph_is_dropped_from_the_text_and_kept_as_a_markdown_list() -> None:
    content = pdf_bytes("<ul><li>first point</li><li>second point</li></ul>")

    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = PdfPlumberLabelerMarkdown().source(content=content)

    assert _texts(chunks) == ["first point", "second point"]
    assert [chunk.marked_text for chunk in source.chunks] == ["- first point", "- second point"]


def test_labeler_source_carries_the_chunker_anchors_with_markdown() -> None:
    content = pdf_bytes(
        f"<h1>Prov</h1><p>1. {_LONG}</p><p>Svar: <i>ja</i> och <b>nej</b>.</p>"
        "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>",
        css="table { border-collapse: collapse; } td { border: 1px solid black; padding: 4pt; }",
    )

    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = PdfPlumberLabelerMarkdown().source(content=content)

    assert [chunk.anchor for chunk in source.chunks] == [chunk.anchor for chunk in chunks]
    assert [chunk.text for chunk in source.chunks] == [chunk.text for chunk in chunks]
    assert [chunk.marked_text for chunk in source.chunks] == [
        "# **Prov**",
        f"1. {_LONG}",
        "Svar: <i>ja</i> och **nej**.",
        "| a | b |\n| --- | --- |\n| c | d |",
    ]
    assert (source.images, source.unavailable) == ({}, {})


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"%PDF-1.7 this is not a pdf body", "Filen kunde inte läsas som en PDF-fil (.pdf)."),
        (pdf_bytes("<p></p>"), "PDF-filen saknar läsbart innehåll."),
    ],
    ids=["unreadable", "no-text"],
)
def test_unreadable_and_textless_pdfs_are_validation_errors(content: bytes, message: str) -> None:
    with pytest.raises(DomainError) as raised:
        PdfPlumberExamChunker().chunk(content=content)

    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert raised.value.message == message
