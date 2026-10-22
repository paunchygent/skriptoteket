"""Challenge the drawer's preset geometries, flips and rotation with pixel checks on the PNG."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_drawing import (  # noqa: E501
    draw_shape_figure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    LabelerSourceImageUnavailable,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_drawing_test_support import (
    _at,
    _column_ink,
    _draw,
    _figure,
    _ink_box,
    _is_dark,
    _is_red,
    _is_white,
    _row_ink,
    _shape,
)

pytestmark = pytest.mark.unit


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
