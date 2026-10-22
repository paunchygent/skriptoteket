"""Challenge the drawer's shape labels, and the corpus figures they appear in, on the PNG."""

from __future__ import annotations

import pytest
from PIL import Image

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    FigureShape,
    LabelAnchor,
    LabelParagraph,
    LabelRun,
    ShapeFigure,
    ShapeLabel,
    ShapeOutline,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_drawing_test_support import (
    _PX,
    Box,
    _at,
    _draw,
    _figure,
    _ink_box,
    _is_dark,
    _is_red,
    _is_white,
    _pixel,
    _shape,
    _transitions,
)

pytestmark = pytest.mark.unit


def _label(
    text: str,
    *,
    size_pt: float = 12.0,
    color: str = "000000",
    anchor: LabelAnchor = "ctr",
    bold: bool = False,
    inset_px: int = 4,
) -> ShapeLabel:
    return ShapeLabel(
        paragraphs=(
            LabelParagraph(
                runs=(LabelRun(text, size_pt, color, bold=bold),),
                align="center",
            ),
        ),
        inset_left_emu=inset_px * _PX,
        inset_top_emu=inset_px * _PX,
        inset_right_emu=inset_px * _PX,
        inset_bottom_emu=inset_px * _PX,
        anchor=anchor,
    )


def _text_pixels(image: Image.Image, box: Box) -> list[tuple[int, int]]:
    """Dark pixels inside the drawn box, away from its outline."""
    left, top, right, bottom = box
    margin = 12
    return [
        (x, y)
        for y in range(top + margin, bottom - margin)
        for x in range(left + margin, right - margin)
        if _is_dark(_pixel(image, x, y))
    ]


def _centroid(points: list[tuple[int, int]]) -> tuple[float, float]:
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def test_centred_label_text_lands_in_the_middle_third() -> None:
    shape = _shape("rect", 200, 100, fill="FFFF00", label=_label("Hej"))
    image = _draw(_figure(shape))
    box = _ink_box(image)
    points = _text_pixels(image, box)
    assert len(points) > 20
    cx, cy = _centroid(points)
    left, top, right, bottom = box
    assert left + (right - left) / 3 < cx < right - (right - left) / 3
    assert top + (bottom - top) / 3 < cy < bottom - (bottom - top) / 3


def test_label_anchor_places_text_top_and_bottom() -> None:
    def centroid_y(anchor: LabelAnchor) -> float:
        shape = _shape("rect", 200, 120, fill=None, label=_label("Hej", anchor=anchor))
        image = _draw(_figure(shape, height_px=120))
        box = _ink_box(image)
        return (_centroid(_text_pixels(image, box))[1] - box[1]) / (box[3] - box[1])

    assert centroid_y("t") < 0.3
    assert 0.4 < centroid_y("ctr") < 0.6
    assert centroid_y("b") > 0.7


def test_long_label_wraps_inside_the_shape() -> None:
    text = "Svenska gymnasieelever som läser ett högskoleförberedande program"
    shape = _shape("rect", 140, 120, fill=None, label=_label(text, size_pt=10.0))
    image = _draw(_figure(shape, width_px=140, height_px=120))
    box = _ink_box(image)
    points = _text_pixels(image, box)
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    # Text stays between the outline's inner edges and takes several lines.
    assert min(xs) > box[0] + 4 and max(xs) < box[2] - 4
    assert max(ys) - min(ys) > 2.5 * 10.0 * 1.33 * 1.5


def test_label_turns_with_its_shape() -> None:
    shape = _shape(
        "rect", 200, 40, fill=None, rotation_deg=90.0, label=_label("Lodrät text", size_pt=11.0)
    )
    image = _draw(_figure(shape, width_px=200, height_px=200))
    box = _ink_box(image)
    points = _text_pixels(image, box)
    xs, ys = [x for x, _ in points], [y for _, y in points]
    assert len(points) > 20
    assert max(ys) - min(ys) > 2 * (max(xs) - min(xs))


def test_label_run_colour_is_drawn() -> None:
    shape = _shape("rect", 200, 100, fill=None, label=_label("Rött", color="FF0000", bold=True))
    image = _draw(_figure(shape))
    box = _ink_box(image)
    left, top, right, bottom = box
    reds = sum(
        _is_red(_pixel(image, x, y))
        for y in range(top + 10, bottom - 10)
        for x in range(left + 10, right - 10)
    )
    assert reds > 20


def test_label_text_is_escaped() -> None:
    shape = _shape("rect", 200, 100, fill=None, label=_label("a < b & <i>c</i>"))
    image = _draw(_figure(shape))
    assert len(_text_pixels(image, _ink_box(image))) > 50


def test_ellipse_label_wraps_inside_the_inscribed_rectangle() -> None:
    text = "Svenska gymnasieelever (populationen)"
    faint = ShapeOutline("C8C8C8", 2 * _PX)  # not dark, so the text pixels stand alone
    shape = _shape(
        "ellipse", 300, 140, fill=None, outline=faint, label=_label(text, size_pt=10.0, anchor="t")
    )
    image = _draw(_figure(shape, width_px=300, height_px=140))
    box = _ink_box(image)
    points = _text_pixels(image, box)
    xs = [x for x, _ in points]
    width = box[2] - box[0]
    # The inscribed rectangle is 71 percent of the ellipse's width.
    assert max(xs) - min(xs) < 0.75 * width
    assert min(xs) > box[0] + 0.1 * width


def _fixture_population() -> ShapeFigure:
    outline = ShapeOutline("000000", 19050)

    def label(text: str, anchor: LabelAnchor) -> ShapeLabel:
        return ShapeLabel(
            paragraphs=(LabelParagraph(runs=(LabelRun(text, 10.0, "000000"),), align="center"),),
            inset_left_emu=36000,
            inset_top_emu=36000,
            inset_right_emu=36000,
            inset_bottom_emu=36000,
            anchor=anchor,
        )

    return ShapeFigure(
        width_emu=4320000,
        height_emu=1655999,
        shapes=(
            FigureShape(
                "ellipse",
                0,
                0,
                4320000,
                1655999,
                fill=None,
                outline=outline,
                label=label("Svenska gymnasieelever (populationen)", "t"),
            ),  # fmt: skip
            FigureShape(
                "ellipse",
                2232000,
                684000,
                1800000,
                827999,
                fill="DDEBF7",
                outline=outline,
                label=label("Elever på ett program (urvalet)", "ctr"),
            ),  # fmt: skip
        ),
    )


def _fixture_process() -> ShapeFigure:
    outline = ShapeOutline("000000", 19050)

    def label(text: str) -> ShapeLabel:
        return ShapeLabel(
            paragraphs=(LabelParagraph(runs=(LabelRun(text, 10.0, "000000"),), align="center"),),
            inset_left_emu=36000,
            inset_top_emu=36000,
            inset_right_emu=36000,
            inset_bottom_emu=36000,
            anchor="ctr",
        )

    def box(x: int, text: str) -> FigureShape:
        return FigureShape(
            "rect", x, 0, 1296000, 864000, fill=None, outline=outline, label=label(text)
        )

    def arrow(x: int) -> FigureShape:
        return FigureShape("rightArrow", x, 288000, 432000, 288000, fill="404040", outline=outline)

    return ShapeFigure(
        width_emu=5040000,
        height_emu=864000,
        shapes=(
            box(0, "Planering"),
            arrow(1404000),
            box(1908000, "Genomförande"),
            arrow(3311999),
            box(3744000, "Utvärdering"),
        ),
    )


def test_population_fixture_draws_both_ellipses_with_their_labels() -> None:
    image = _draw(_fixture_population())
    box = _ink_box(image)
    assert box[2] - box[0] > 1.5 * 4320000 / _PX * 0.9
    # The inner ellipse's light blue fill is present, the outer ellipse is not filled.
    blue = sum(
        1
        for y in range(box[1], box[3], 3)
        for x in range(box[0], box[2], 3)
        if image.getpixel((x, y)) == (221, 235, 247)
    )
    assert blue > 200
    assert _is_white(_at(image, box, 0.5, 0.35))  # the outer ellipse is not filled
    assert len(_text_pixels(image, box)) > 200


def test_process_fixture_draws_three_boxes_and_two_arrows() -> None:
    image = _draw(_fixture_process())
    box = _ink_box(image)
    grey = sum(
        1
        for y in range(box[1], box[3], 2)
        for x in range(box[0], box[2], 2)
        if image.getpixel((x, y)) == (64, 64, 64)
    )
    assert grey > 100
    assert len(_text_pixels(image, box)) > 200
    # Three boxes cross the middle row of the figure's top edge.
    assert _transitions(image, box, 0.02) >= 5
