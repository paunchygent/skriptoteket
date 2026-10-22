"""PDF drawn figures and their labels land in their questions (TASK-SKRIPT-39-10-02)."""

from __future__ import annotations

from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_picture_test_support import (
    assert_drawing_chunk,
    ink_box,
    pdf_chunks,
    triangle_figure,
)

# Union of the triangle corners and the label anchors in triangle_figure: x 20..180, y 12..144.
_TRIANGLE_ASPECT = 160 / 132
_GENEROUS_CUT_TOLERANCE = 0.15
_MIN_CUT_MARGIN_PX = 3

_ANSWER_LINES_SVG = (
    '<svg width="300" height="60" xmlns="http://www.w3.org/2000/svg">'
    '<line x1="0" y1="10" x2="300" y2="10" stroke="black" stroke-width="1"/>'
    '<line x1="0" y1="35" x2="300" y2="35" stroke="black" stroke-width="1"/>'
    '<line x1="0" y1="60" x2="300" y2="60" stroke="black" stroke-width="1"/>'
    "</svg>"
)


def _assert_generous_cut(payload: bytes, *, expected_aspect: float) -> None:
    (left, top, right, bottom), (width, height) = ink_box(payload)
    assert left >= _MIN_CUT_MARGIN_PX
    assert top >= _MIN_CUT_MARGIN_PX
    assert width - 1 - right >= _MIN_CUT_MARGIN_PX
    assert height - 1 - bottom >= _MIN_CUT_MARGIN_PX
    ink_aspect = (right - left + 1) / (bottom - top + 1)
    assert abs(ink_aspect - expected_aspect) / expected_aspect <= _GENEROUS_CUT_TOLERANCE


def test_drawn_triangle_with_labels_becomes_one_generous_drawing_chunk() -> None:
    chunks = pdf_chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002", "body:0003"]
    payload = assert_drawing_chunk(chunks[1], anchor="body:0002")
    _assert_generous_cut(payload, expected_aspect=_TRIANGLE_ASPECT)


def test_figure_labels_are_not_emitted_as_text() -> None:
    labels = ("A", "B", "C")
    chunks = pdf_chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{triangle_figure(labels)}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    texts = [chunk.text for chunk in chunks if chunk.kind != "drawing"]
    assert texts == ["Fråga 1. Beskriv triangeln med hörnen.", "Fråga 2. Gå vidare."]
    words = {word for text in texts for word in text.split()}
    assert not (set(labels) & words)


def test_drawn_answer_lines_under_svar_give_no_drawing_chunk() -> None:
    chunks = pdf_chunks(f"<p>Svar:</p><p>{_ANSWER_LINES_SVG}</p>")

    assert all(chunk.kind != "drawing" for chunk in chunks)
    assert "Svar:" in [chunk.text for chunk in chunks]


def test_two_drawn_figures_separated_by_a_paragraph_give_two_drawing_chunks_in_order() -> None:  # noqa: E501
    chunks = pdf_chunks(
        "<p>Fråga 1. Beskriv den första triangeln.</p>"
        f"<p>{triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 2. Jämför med nästa triangel.</p>"
        f"<p>{triangle_figure(('D', 'E', 'F'))}</p>"
        "<p>Fråga 3. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "drawing",
        "paragraph",
        "drawing",
        "paragraph",
    ]
    assert [chunk.anchor for chunk in chunks] == [f"body:{index:04d}" for index in range(1, 6)]
    assert chunks[2].text == "Fråga 2. Jämför med nästa triangel."
    first = assert_drawing_chunk(chunks[1], anchor="body:0002")
    second = assert_drawing_chunk(chunks[3], anchor="body:0004")
    assert first != second


def test_empty_bordered_table_becomes_one_drawing_chunk_and_no_table_chunk() -> None:
    chunks = pdf_chunks(
        "<p>Före tabellen.</p>"
        "<table><tr><td></td><td></td><td></td></tr>"
        "<tr><td></td><td></td><td></td></tr>"
        "<tr><td></td><td></td><td></td></tr></table>"
        "<p>Efter tabellen.</p>",
        css="table { border-collapse: collapse; } td { border: 1px solid black; "
        "width: 40pt; height: 40pt; }",
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks] == ["Före tabellen.", "", "Efter tabellen."]
    assert_drawing_chunk(chunks[1], anchor="body:0002")


def test_italic_answer_line_under_a_triangle_is_a_label_accepted_residual() -> None:
    chunks = pdf_chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="180"><polygon points="40,130 200,130 120,20" '
        'fill="none" stroke="black"/>'
        '<text x="80" y="145" font-size="11" font-style="italic">Svar: 42 cm</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "drawing",
        "paragraph",
    ]
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "Svar" not in joined and "42" not in joined
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    # The cut covers the triangle (y 20..130) and the answer under it (to about y 148).
    _assert_generous_cut(
        assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=160 / 128,
    )


def test_plain_rectangle_with_dimension_keeps_dimension_in_figure() -> None:
    chunks = pdf_chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="180"><rect x="40" y="30" width="150" height="100" '
        'fill="none" stroke="black"/>'
        '<text x="90" y="150" font-size="12">8 cm</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert drawings[0] is chunks[1]
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "8" not in joined.split()
    assert "cm" not in joined
    # The cut covers the rectangle (y 30..130) and the dimension under it.
    _assert_generous_cut(
        assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=150 / 125,
    )


def test_chart_tick_and_title_are_labels_in_figure() -> None:
    chunks = pdf_chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="200">'
        '<polyline points="40,20 40,130 200,130" fill="none" stroke="black"/>'
        '<polyline points="40,120 90,100 140,70 200,40" fill="none" stroke="black"/>'
        '<text x="90" y="143" font-size="12">10</text>'
        '<text x="90" y="164" font-size="12">Tid (sekunder)</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "10" not in joined.split()
    assert "Tid" not in joined and "sekunder" not in joined
    # The cut covers the axes (y 20..130), the tick and the title under them.
    _assert_generous_cut(
        assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=160 / 147,
    )


def test_two_triangles_side_by_side_keep_their_own_labels() -> None:
    chunks = pdf_chunks(
        "<p>1. Jämför trianglarna.</p>"
        f"<p>{triangle_figure(('A', 'B', 'C'))}{triangle_figure(('D', 'E', 'F'))}</p>"
        "<p>2. Fortsätt.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "drawing", "paragraph"]
    assert [chunk.anchor for chunk in chunks] == [f"body:{index:04d}" for index in range(1, 5)]
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert not (set(("A", "B", "C", "D", "E", "F")) & set(joined.split()))
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert drawings[0].anchor == "body:0002"
    assert drawings[1].anchor == "body:0003"
    first = assert_drawing_chunk(drawings[0], anchor="body:0002")
    second = assert_drawing_chunk(drawings[1], anchor="body:0003")
    assert first != second
    _assert_generous_cut(first, expected_aspect=_TRIANGLE_ASPECT)
    _assert_generous_cut(second, expected_aspect=_TRIANGLE_ASPECT)
