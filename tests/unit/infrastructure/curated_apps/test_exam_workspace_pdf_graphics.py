"""Unit tests for the pure PDF page-graphics classifier on hand-built boxes."""

from __future__ import annotations

from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_graphics import (  # noqa: E501
    PageGraphics,
    PdfCut,
    PdfStroke,
    page_cuts,
)

_BODY = 11.0
_WIDTH = 595.0
_HEIGHT = 842.0


def _page(
    *,
    images: tuple[tuple[float, float, float, float], ...] = (),
    strokes: tuple[PdfStroke, ...] = (),
    words: tuple[tuple[float, float, float, float], ...] = (),
    lines: tuple[tuple[int, ...], ...] = (),
    tables: tuple[tuple[float, float, float, float], ...] = (),
    text_left: float = 0.0,
) -> PageGraphics:
    return PageGraphics(
        width=_WIDTH,
        height=_HEIGHT,
        images=images,
        strokes=strokes,
        words=words,
        lines=lines,
        tables=tables,
        text_left=text_left,
    )


def _stroke(
    box: tuple[float, float, float, float],
    kind: Literal["line", "rect", "curve"] = "line",
    *,
    stroked: bool = True,
    filled: bool = False,
) -> PdfStroke:
    return PdfStroke(box=box, kind=kind, stroked=stroked, filled=filled)


def _triangle() -> tuple[PdfStroke, ...]:
    return (
        _stroke((100.0, 178.0, 200.0, 180.0)),
        _stroke((100.0, 100.0, 150.0, 180.0)),
        _stroke((150.0, 100.0, 200.0, 180.0)),
    )


def test_image_alone_is_picture_with_inside_label() -> None:
    image = (100.0, 200.0, 300.0, 400.0)
    cuts = page_cuts(
        _page(
            images=(image,),
            words=((150.0, 250.0, 200.0, 260.0), (400.0, 500.0, 450.0, 510.0)),
            lines=((0,), (1,)),
        ),
        body_size=_BODY,
    )
    assert cuts == (PdfCut(kind="picture", box=image, labels=frozenset({0})),)


def test_triangle_with_outside_words_has_no_labels() -> None:
    words = (
        (84.0, 140.0, 98.0, 148.0),
        (202.0, 140.0, 214.0, 148.0),
        (140.0, 182.0, 160.0, 188.0),
    )
    cuts = page_cuts(
        _page(strokes=_triangle(), words=words, lines=((0,), (1,), (2,))),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    cut = cuts[0]
    assert cut.kind == "figure"
    assert cut.labels == frozenset()
    assert cut.box == (99.0, 89.0, 201.0, 181.0)


def test_wide_sentence_line_is_not_label_and_stops_margin() -> None:
    strokes = (_stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),)
    words = (
        (50.0, 185.0, 120.0, 193.0),
        (125.0, 185.0, 200.0, 193.0),
        (205.0, 185.0, 300.0, 193.0),
    )
    cuts = page_cuts(
        _page(strokes=strokes, words=words, lines=((0, 1, 2),)),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    cut = cuts[0]
    assert cut.kind == "figure"
    assert cut.labels == frozenset()
    assert cut.box == (89.0, 89.0, 211.0, 184.0)


def test_short_lines_near_figure_are_body_text_not_labels() -> None:
    strokes = (_stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),)
    words = ((100.0, 182.0, 130.0, 193.0), (133.0, 182.0, 180.0, 193.0))
    margin_page = _page(strokes=strokes, words=words, lines=((0, 1),), text_left=100.0)
    indented_page = _page(strokes=strokes, words=words, lines=((0, 1),), text_left=70.0)

    assert page_cuts(margin_page, body_size=_BODY)[0].labels == frozenset()
    assert page_cuts(indented_page, body_size=_BODY)[0].labels == frozenset()


def test_page_sized_picture_is_a_picture_cut_without_labels() -> None:
    image = (0.0, 0.0, _WIDTH, _HEIGHT)
    words = ((70.0, 100.0, 120.0, 111.0), (125.0, 100.0, 200.0, 111.0))
    page = _page(images=(image,), words=words, lines=((0, 1),), text_left=70.0)

    assert page_cuts(page, body_size=_BODY) == (
        PdfCut(kind="picture", box=image, labels=frozenset()),
    )


def test_picture_behind_a_paragraph_claims_none_of_its_words() -> None:
    words = ((70.0, 100.0, 120.0, 111.0), (125.0, 100.0, 200.0, 111.0))
    page = _page(
        images=((100.0, 90.0, 300.0, 200.0),), words=words, lines=((0, 1),), text_left=70.0
    )

    cuts = page_cuts(page, body_size=_BODY)

    assert [(cut.kind, cut.labels) for cut in cuts] == [("picture", frozenset())]


def test_stacked_answer_lines_make_no_cut() -> None:
    strokes = (
        _stroke((100.0, 100.0, 300.0, 101.0)),
        _stroke((100.0, 120.0, 300.0, 121.0)),
        _stroke((100.0, 140.0, 300.0, 141.0)),
    )
    assert page_cuts(_page(strokes=strokes), body_size=_BODY) == ()


def test_box_holding_indented_word_is_figure_and_checkbox_makes_no_cut() -> None:
    strokes = (
        _stroke((100.0, 100.0, 300.0, 120.0), kind="rect"),
        _stroke((100.0, 200.0, 108.0, 208.0), kind="rect"),
    )
    cuts = page_cuts(
        _page(
            strokes=strokes,
            words=((120.0, 104.0, 200.0, 116.0),),
            lines=((0,),),
        ),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].labels == frozenset()
    assert cuts[0].box == (89.0, 89.0, 311.0, 131.0)


def test_highlight_rect_behind_word_makes_no_cut() -> None:
    strokes = (_stroke((100.0, 100.0, 200.0, 112.0), kind="rect", stroked=False, filled=True),)
    cuts = page_cuts(
        _page(
            strokes=strokes,
            words=((110.0, 102.0, 150.0, 110.0),),
            lines=((0,),),
        ),
        body_size=_BODY,
    )
    assert cuts == ()


def test_strokes_inside_table_make_no_cut() -> None:
    strokes = (_stroke((120.0, 120.0, 280.0, 180.0), kind="rect"),)
    cuts = page_cuts(
        _page(strokes=strokes, tables=((100.0, 100.0, 300.0, 200.0),)),
        body_size=_BODY,
    )
    assert cuts == ()


def test_two_figures_sort_top_to_bottom() -> None:
    strokes = (
        _stroke((100.0, 300.0, 200.0, 380.0), kind="curve"),
        _stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),
    )
    cuts = page_cuts(_page(strokes=strokes), body_size=_BODY)
    assert [cut.kind for cut in cuts] == ["figure", "figure"]
    assert cuts[0].box == (89.0, 89.0, 211.0, 191.0)
    assert cuts[1].box == (89.0, 289.0, 211.0, 391.0)


def test_page_border_rect_is_ignored_and_curve_stays_figure() -> None:
    strokes = (
        _stroke((0.0, 0.0, _WIDTH, _HEIGHT), kind="rect", filled=True),
        _stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),
    )
    words = ((70.0, 500.0, 120.0, 510.0), (125.0, 500.0, 180.0, 510.0))
    cuts = page_cuts(
        _page(strokes=strokes, words=words, lines=((0, 1),), text_left=70.0),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].box == (89.0, 89.0, 211.0, 191.0)


def test_triangle_with_indented_answer_line_below_has_no_labels() -> None:
    words = ((120.0, 183.0, 150.0, 193.0), (153.0, 183.0, 190.0, 193.0))
    cuts = page_cuts(
        _page(strokes=_triangle(), words=words, lines=((0, 1),), text_left=70.0),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    cut = cuts[0]
    assert cut.kind == "figure"
    assert cut.labels == frozenset()
    assert cut.box[3] < 183.0


def test_rect_with_word_below_is_figure_without_labels() -> None:
    cuts = page_cuts(
        _page(
            strokes=(_stroke((40.0, 30.0, 190.0, 130.0), kind="rect"),),
            words=((100.0, 133.0, 140.0, 143.0),),
            lines=((0,),),
            text_left=70.0,
        ),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].labels == frozenset()
    assert cuts[0].box[3] < 133.0


def test_four_lines_forming_box_is_figure() -> None:
    strokes = (
        _stroke((40.0, 30.0, 190.0, 32.0)),
        _stroke((40.0, 128.0, 190.0, 130.0)),
        _stroke((40.0, 30.0, 42.0, 130.0)),
        _stroke((188.0, 30.0, 190.0, 130.0)),
    )
    cuts = page_cuts(_page(strokes=strokes), body_size=_BODY)
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"


def test_rect_holding_indented_line_is_figure_without_labels() -> None:
    words = ((60.0, 70.0, 100.0, 80.0), (105.0, 70.0, 150.0, 80.0))
    cuts = page_cuts(
        _page(
            strokes=(_stroke((40.0, 30.0, 190.0, 130.0), kind="rect"),),
            words=words,
            lines=((0, 1),),
            text_left=70.0,
        ),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].labels == frozenset()


def test_rect_holding_margin_line_is_border_without_cut() -> None:
    words = ((70.0, 70.0, 110.0, 80.0), (115.0, 70.0, 150.0, 80.0))
    cuts = page_cuts(
        _page(
            strokes=(_stroke((40.0, 30.0, 190.0, 130.0), kind="rect"),),
            words=words,
            lines=((0, 1),),
            text_left=70.0,
        ),
        body_size=_BODY,
    )
    assert cuts == ()


def test_page_border_rect_is_dropped_and_inner_curve_is_figure() -> None:
    strokes = (
        _stroke((0.0, 0.0, _WIDTH, _HEIGHT), kind="rect"),
        _stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),
    )
    words = ((70.0, 500.0, 120.0, 510.0), (125.0, 500.0, 180.0, 510.0))
    cuts = page_cuts(
        _page(strokes=strokes, words=words, lines=((0, 1),), text_left=70.0),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].box == (89.0, 89.0, 211.0, 191.0)


def test_large_picture_between_paragraphs_is_picture() -> None:
    image = (87.0, 100.0, 507.0, 710.0)
    words = (
        (70.0, 80.0, 120.0, 90.0),
        (125.0, 80.0, 180.0, 90.0),
        (70.0, 720.0, 120.0, 730.0),
        (125.0, 720.0, 180.0, 730.0),
    )
    cuts = page_cuts(
        _page(images=(image,), words=words, lines=((0, 1), (2, 3)), text_left=70.0),
        body_size=_BODY,
    )
    assert cuts == (PdfCut(kind="picture", box=image, labels=frozenset()),)


def test_axis_with_tick_and_title_has_no_labels() -> None:
    strokes = (
        _stroke((40.0, 120.0, 200.0, 122.0)),
        _stroke((40.0, 20.0, 42.0, 120.0)),
        _stroke((50.0, 30.0, 190.0, 110.0), kind="curve"),
    )
    words = ((90.0, 123.0, 110.0, 133.0), (80.0, 145.0, 170.0, 155.0))
    cuts = page_cuts(
        _page(strokes=strokes, words=words, lines=((0,), (1,)), text_left=70.0),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].kind == "figure"
    assert cuts[0].labels == frozenset()
    assert cuts[0].box[3] < 123.0


def test_line_straddling_hull_gives_none_of_its_words_while_inside_labels_stay() -> None:
    strokes = (_stroke((100.0, 100.0, 200.0, 180.0), kind="curve"),)
    words = (
        (120.0, 120.0, 150.0, 130.0),
        (210.0, 120.0, 250.0, 130.0),
        (255.0, 120.0, 290.0, 130.0),
        (130.0, 150.0, 140.0, 160.0),
    )
    cuts = page_cuts(
        _page(strokes=strokes, words=words, lines=((0, 1, 2), (3,))),
        body_size=_BODY,
    )
    assert len(cuts) == 1
    assert cuts[0].labels == frozenset({3})


def test_filled_rectangle_without_outline_is_a_figure() -> None:
    strokes = (_stroke((100.0, 100.0, 250.0, 200.0), kind="rect", stroked=False, filled=True),)
    cuts = page_cuts(_page(strokes=strokes), body_size=_BODY)
    assert [(cut.kind, cut.labels) for cut in cuts] == [("figure", frozenset())]
