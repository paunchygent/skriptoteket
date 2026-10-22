"""Challenge the drawer of Word shape figures with pixel checks on the rendered PNG."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_drawing import (  # noqa: E501
    draw_shape_figure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    Arrowhead,
    FigureShape,
    LabelAnchor,
    LabelParagraph,
    LabelRun,
    PresetGeometry,
    ShapeFigure,
    ShapeLabel,
    ShapeOutline,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    LabelerSourceImageUnavailable,
)

pytestmark = pytest.mark.unit

_EMU_PER_PX = 9525
_PX = _EMU_PER_PX  # one CSS pixel in EMU
_BLACK = ShapeOutline(color="000000", width_emu=2 * _PX)

Box = tuple[int, int, int, int]


def _shape(
    preset: PresetGeometry,
    width_px: int,
    height_px: int,
    *,
    fill: str | None = "FF0000",
    outline: ShapeOutline | None = _BLACK,
    x_px: int = 0,
    y_px: int = 0,
    **options: object,
) -> FigureShape:
    return FigureShape(
        preset=preset,
        x_emu=x_px * _PX,
        y_emu=y_px * _PX,
        width_emu=width_px * _PX,
        height_emu=height_px * _PX,
        fill=fill,
        outline=outline,
        **options,  # type: ignore[arg-type]
    )


def _figure(*shapes: FigureShape, width_px: int = 200, height_px: int = 120) -> ShapeFigure:
    return ShapeFigure(width_px * _PX, height_px * _PX, tuple(shapes))


def _draw(figure: ShapeFigure) -> Image.Image:
    content = draw_shape_figure(figure, anchor="body:0001")
    image = Image.open(io.BytesIO(content))
    image.load()
    assert image.format == "PNG"
    return image.convert("RGB")


def _is_ink(pixel: tuple[int, int, int]) -> bool:
    return min(pixel) < 235


def _ink_box(image: Image.Image) -> Box:
    box = image.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox()
    assert box is not None
    return box


def _at(image: Image.Image, box: Box, fx: float, fy: float) -> tuple[int, int, int]:
    """The pixel at a fraction of the drawn content's box (0, 0 is its top left)."""
    left, top, right, bottom = box
    x = min(right - 1, max(left, round(left + fx * (right - left))))
    y = min(bottom - 1, max(top, round(top + fy * (bottom - top))))
    pixel = image.getpixel((x, y))
    assert isinstance(pixel, tuple)
    return pixel[0], pixel[1], pixel[2]


def _column_ink(image: Image.Image, box: Box, fx: float) -> int:
    left, top, right, bottom = box
    x = min(right - 1, round(left + fx * (right - left)))
    return sum(_is_ink(image.getpixel((x, y))) for y in range(top, bottom))  # type: ignore[arg-type]


def _row_ink(image: Image.Image, box: Box, fy: float) -> int:
    left, top, right, bottom = box
    y = min(bottom - 1, round(top + fy * (bottom - top)))
    return sum(_is_ink(image.getpixel((x, y))) for x in range(left, right))  # type: ignore[arg-type]


def _is_red(pixel: tuple[int, int, int]) -> bool:
    return pixel[0] > 200 and pixel[1] < 60 and pixel[2] < 60


def _is_white(pixel: tuple[int, int, int]) -> bool:
    return min(pixel) > 245


def _is_dark(pixel: tuple[int, int, int]) -> bool:
    return max(pixel) < 100


def test_rect_fills_to_its_corners() -> None:
    image = _draw(_figure(_shape("rect", 160, 80)))
    box = _ink_box(image)
    assert _is_red(_at(image, box, 0.5, 0.5))
    assert not _is_white(_at(image, box, 0.02, 0.03))
    assert not _is_white(_at(image, box, 0.98, 0.97))
    # The outline is black and sits on the box edge.
    assert _is_dark(_at(image, box, 0.5, 0.0))


def test_round_rect_corners_are_lighter_than_rect_corners() -> None:
    rounded = _draw(_figure(_shape("roundRect", 160, 80)))
    plain = _draw(_figure(_shape("rect", 160, 80)))
    rounded_box, plain_box = _ink_box(rounded), _ink_box(plain)
    assert _is_white(_at(rounded, rounded_box, 0.01, 0.02))
    assert not _is_white(_at(plain, plain_box, 0.01, 0.02))
    assert _is_red(_at(rounded, rounded_box, 0.5, 0.5))


def test_round_rect_adjustment_widens_the_corner() -> None:
    small = _draw(_figure(_shape("roundRect", 160, 80, adjustments=(("adj", 5000),))))
    large = _draw(_figure(_shape("roundRect", 160, 80, adjustments=(("adj", 50000),))))
    assert not _is_white(_at(small, _ink_box(small), 0.04, 0.08))
    assert _is_white(_at(large, _ink_box(large), 0.04, 0.08))


def test_ellipse_has_white_corners_and_filled_centre() -> None:
    image = _draw(_figure(_shape("ellipse", 160, 90)))
    box = _ink_box(image)
    for fx, fy in ((0.03, 0.03), (0.97, 0.03), (0.03, 0.97), (0.97, 0.97)):
        assert _is_white(_at(image, box, fx, fy))
    assert _is_red(_at(image, box, 0.5, 0.5))
    assert _is_red(_at(image, box, 0.2, 0.5))


def test_triangle_apex_is_on_top_and_base_is_full() -> None:
    image = _draw(_figure(_shape("triangle", 160, 100)))
    box = _ink_box(image)
    assert _is_white(_at(image, box, 0.1, 0.1))
    assert _is_white(_at(image, box, 0.9, 0.1))
    assert not _is_white(_at(image, box, 0.5, 0.06))
    assert _is_red(_at(image, box, 0.12, 0.9))
    assert _row_ink(image, box, 0.9) > 2 * _row_ink(image, box, 0.2)


def test_triangle_adjustment_moves_the_apex() -> None:
    image = _draw(_figure(_shape("triangle", 160, 100, adjustments=(("adj", 0),))))
    box = _ink_box(image)
    assert not _is_white(_at(image, box, 0.03, 0.06))
    assert _is_white(_at(image, box, 0.7, 0.2))


def test_right_triangle_has_its_right_angle_at_the_bottom_left() -> None:
    image = _draw(_figure(_shape("rtTriangle", 160, 100)))
    box = _ink_box(image)
    assert _is_red(_at(image, box, 0.1, 0.9))
    assert _is_white(_at(image, box, 0.9, 0.1))
    assert not _is_white(_at(image, box, 0.03, 0.05))


def test_line_runs_corner_to_corner_without_fill() -> None:
    line = _shape("line", 160, 100, fill="FF0000")
    image = _draw(_figure(line))
    box = _ink_box(image)
    assert _is_dark(_at(image, box, 0.5, 0.5))
    assert _is_white(_at(image, box, 0.85, 0.15))
    assert _is_white(_at(image, box, 0.15, 0.85))
    assert not any(_is_red(_at(image, box, f, 1 - f)) for f in (0.2, 0.4, 0.6, 0.8))


def test_line_without_outline_draws_nothing() -> None:
    with pytest.raises(LabelerSourceImageUnavailable) as raised:
        draw_shape_figure(_figure(_shape("line", 160, 100, outline=None)), anchor="body:0042")
    assert raised.value.anchor == "body:0042"


def test_flipped_line_runs_from_the_top_right_to_the_bottom_left() -> None:
    image = _draw(_figure(_shape("line", 160, 100, flip_h=True)))
    box = _ink_box(image)
    assert _is_dark(_at(image, box, 0.5, 0.5))
    assert _is_dark(_at(image, box, 0.85, 0.15))
    assert _is_white(_at(image, box, 0.15, 0.15))


def test_connector_tail_arrowhead_is_a_thick_dark_end() -> None:
    outline = ShapeOutline("000000", 2 * _PX, tail=Arrowhead("triangle", "lg", "lg"))
    image = _draw(_figure(_shape("straightConnector1", 200, 0, outline=outline, fill=None)))
    box = _ink_box(image)
    middle = _column_ink(image, box, 0.5)
    near_tail = _column_ink(image, box, 0.96)
    near_head = _column_ink(image, box, 0.03)
    assert near_tail >= 2 * middle
    assert near_head <= middle + 1
    assert _is_dark(_at(image, box, 0.96, 0.5))


def test_connector_head_arrowhead_sits_at_the_path_start() -> None:
    outline = ShapeOutline("000000", 2 * _PX, head=Arrowhead("triangle", "lg", "lg"))
    image = _draw(_figure(_shape("straightConnector1", 200, 0, outline=outline, fill=None)))
    box = _ink_box(image)
    assert _column_ink(image, box, 0.04) >= 2 * _column_ink(image, box, 0.5)
    assert _column_ink(image, box, 0.97) <= _column_ink(image, box, 0.5) + 1


@pytest.mark.parametrize("kind", ["arrow", "stealth", "oval", "diamond"])
def test_every_arrowhead_kind_widens_the_line_end(kind: str) -> None:
    outline = ShapeOutline("000000", 2 * _PX, tail=Arrowhead(kind, "lg", "lg"))  # type: ignore[arg-type]
    image = _draw(_figure(_shape("line", 200, 0, outline=outline, fill=None)))
    box = _ink_box(image)
    widest = max(_column_ink(image, box, f / 100) for f in range(80, 100, 2))
    assert widest >= 2 * _column_ink(image, box, 0.4)


def test_diagonal_arrowhead_follows_the_line_direction() -> None:
    outline = ShapeOutline("000000", 4 * _PX, tail=Arrowhead("triangle", "lg", "lg"))
    image = _draw(_figure(_shape("line", 160, 160, outline=outline, fill=None)))
    box = _ink_box(image)
    # Beside the tip, off the diagonal both ways, the head has ink and the shaft has none.
    assert not _is_white(_at(image, box, 0.965, 0.918))
    assert not _is_white(_at(image, box, 0.918, 0.965))
    assert _is_white(_at(image, box, 0.5, 0.42))


def test_right_arrow_head_is_on_the_right() -> None:
    image = _draw(_figure(_shape("rightArrow", 200, 80)))
    box = _ink_box(image)
    assert _column_ink(image, box, 0.8) > 1.5 * _column_ink(image, box, 0.2)
    assert _column_ink(image, box, 0.99) < _column_ink(image, box, 0.8)
    assert _is_red(_at(image, box, 0.3, 0.5))


def test_left_arrow_head_is_on_the_left() -> None:
    image = _draw(_figure(_shape("leftArrow", 200, 80)))
    box = _ink_box(image)
    assert _column_ink(image, box, 0.2) > 1.5 * _column_ink(image, box, 0.8)
    assert _column_ink(image, box, 0.01) < _column_ink(image, box, 0.2)


def test_up_arrow_head_is_on_top() -> None:
    image = _draw(_figure(_shape("upArrow", 80, 200)))
    box = _ink_box(image)
    assert _row_ink(image, box, 0.2) > 1.5 * _row_ink(image, box, 0.8)
    assert _row_ink(image, box, 0.01) < _row_ink(image, box, 0.2)


def test_down_arrow_head_is_at_the_bottom() -> None:
    image = _draw(_figure(_shape("downArrow", 80, 200)))
    box = _ink_box(image)
    assert _row_ink(image, box, 0.8) > 1.5 * _row_ink(image, box, 0.2)
    assert _row_ink(image, box, 0.99) < _row_ink(image, box, 0.8)


def test_arrow_adjustments_change_the_shaft_width() -> None:
    thin = _draw(_figure(_shape("rightArrow", 200, 80, adjustments=(("adj1", 20000),))))
    thick = _draw(_figure(_shape("rightArrow", 200, 80, adjustments=(("adj1", 90000),))))
    assert _column_ink(thick, _ink_box(thick), 0.2) > 2 * _column_ink(thin, _ink_box(thin), 0.2)


def test_flip_h_mirrors_the_shape_inside_its_box() -> None:
    image = _draw(_figure(_shape("rtTriangle", 160, 100, flip_h=True)))
    box = _ink_box(image)
    assert _is_red(_at(image, box, 0.9, 0.9))
    assert _is_white(_at(image, box, 0.1, 0.1))
    assert _is_red(_at(image, box, 0.5, 0.85))  # the base still reaches the left end


def test_flip_v_mirrors_the_shape_inside_its_box() -> None:
    image = _draw(_figure(_shape("triangle", 160, 100, flip_v=True)))
    box = _ink_box(image)
    assert _row_ink(image, box, 0.2) > 2 * _row_ink(image, box, 0.9)


def test_rotation_turns_the_shape_clockwise() -> None:
    image = _draw(_figure(_shape("rightArrow", 200, 80, rotation_deg=90.0), height_px=200))
    box = _ink_box(image)
    assert box[3] - box[1] > box[2] - box[0]
    # A right arrow turned a quarter clockwise points down: the wide head is at the bottom.
    assert _row_ink(image, box, 0.8) > 1.5 * _row_ink(image, box, 0.2)
    assert _row_ink(image, box, 0.99) < _row_ink(image, box, 0.8)


def test_rotated_shape_reaching_outside_the_extent_is_not_clipped() -> None:
    figure = _figure(_shape("rect", 200, 20, x_px=0, y_px=50, rotation_deg=90.0), height_px=120)
    image = _draw(figure)
    box = _ink_box(image)
    # 200 px long, upright after the quarter turn, although the figure is 120 px high.
    assert (box[3] - box[1]) > 1.4 * 200 * 0.9


def test_no_fill_leaves_the_inside_white() -> None:
    image = _draw(_figure(_shape("rect", 160, 80, fill=None)))
    box = _ink_box(image)
    assert _is_white(_at(image, box, 0.5, 0.5))
    assert _is_dark(_at(image, box, 0.5, 0.0))


def test_no_outline_draws_no_stroke() -> None:
    image = _draw(_figure(_shape("rect", 160, 80, outline=None)))
    box = _ink_box(image)
    assert _is_red(_at(image, box, 0.0, 0.0))
    assert _is_red(_at(image, box, 0.5, 0.0))


def test_outline_colour_and_width_are_drawn() -> None:
    thick = ShapeOutline("0000FF", 8 * _PX)
    image = _draw(_figure(_shape("rect", 160, 80, fill=None, outline=thick)))
    box = _ink_box(image)
    pixel = _at(image, box, 0.5, 0.0)
    assert pixel[2] > 200 and pixel[0] < 60
    # A stroke 8 px wide is 12 device pixels; the box edge sits in its middle.
    assert _column_ink(image, box, 0.5) >= 2 * 12


def _transitions(image: Image.Image, box: Box, fy: float) -> int:
    left, top, right, bottom = box
    y = round(top + fy * (bottom - top))
    states = [_is_ink(image.getpixel((x, y))) for x in range(left, right)]  # type: ignore[arg-type]
    return sum(1 for a, b in zip(states, states[1:], strict=False) if a != b)


def test_dashed_outline_has_gaps_and_solid_has_none() -> None:
    dashed = ShapeOutline("000000", 2 * _PX, dash="dash")
    gapped = _draw(_figure(_shape("line", 300, 0, outline=dashed, fill=None), height_px=40))
    solid = _draw(_figure(_shape("line", 300, 0, fill=None), height_px=40))
    assert _transitions(gapped, _ink_box(gapped), 0.5) >= 10
    assert _transitions(solid, _ink_box(solid), 0.5) == 0


@pytest.mark.parametrize("dash", ["dot", "sysDash", "sysDot", "lgDash", "dashDot", "sysDashDot"])
def test_every_dash_style_has_gaps(dash: str) -> None:
    outline = ShapeOutline("000000", 2 * _PX, dash=dash)  # type: ignore[arg-type]
    image = _draw(_figure(_shape("line", 300, 0, outline=outline, fill=None), height_px=40))
    assert _transitions(image, _ink_box(image), 0.5) >= 6


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
        if _is_dark(image.getpixel((x, y)))  # type: ignore[arg-type]
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
        _is_red(image.getpixel((x, y)))  # type: ignore[arg-type]
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
