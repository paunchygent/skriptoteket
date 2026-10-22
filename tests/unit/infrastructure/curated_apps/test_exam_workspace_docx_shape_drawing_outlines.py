"""Challenge the drawer's fills, outlines, arrowheads and dashes with pixel checks on the PNG."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    Arrowhead,
    ArrowheadKind,
    DashStyle,
    ShapeOutline,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_drawing_test_support import (
    _PX,
    _at,
    _column_ink,
    _draw,
    _figure,
    _ink_box,
    _is_dark,
    _is_red,
    _is_white,
    _shape,
    _transitions,
)

pytestmark = pytest.mark.unit


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
def test_every_arrowhead_kind_widens_the_line_end(kind: ArrowheadKind) -> None:
    outline = ShapeOutline("000000", 2 * _PX, tail=Arrowhead(kind, "lg", "lg"))
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


def test_dashed_outline_has_gaps_and_solid_has_none() -> None:
    dashed = ShapeOutline("000000", 2 * _PX, dash="dash")
    gapped = _draw(_figure(_shape("line", 300, 0, outline=dashed, fill=None), height_px=40))
    solid = _draw(_figure(_shape("line", 300, 0, fill=None), height_px=40))
    assert _transitions(gapped, _ink_box(gapped), 0.5) >= 10
    assert _transitions(solid, _ink_box(solid), 0.5) == 0


@pytest.mark.parametrize("dash", ["dot", "sysDash", "sysDot", "lgDash", "dashDot", "sysDashDot"])
def test_every_dash_style_has_gaps(dash: DashStyle) -> None:
    outline = ShapeOutline("000000", 2 * _PX, dash=dash)
    image = _draw(_figure(_shape("line", 300, 0, outline=outline, fill=None), height_px=40))
    assert _transitions(image, _ink_box(image), 0.5) >= 6
