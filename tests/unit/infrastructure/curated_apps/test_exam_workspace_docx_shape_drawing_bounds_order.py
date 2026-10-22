"""Challenge the shape drawer's page bound (F1) and per-shape paint order (F5)."""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageChops

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_shape_drawing as drawing,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_drawing import (  # noqa: E501
    draw_shape_figure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    FigureShape,
    LabelParagraph,
    LabelRun,
    ShapeFigure,
    ShapeLabel,
    ShapeOutline,
    UnsupportedShapeFigure,
)

pytestmark = pytest.mark.unit

_PX = 9525  # one CSS pixel in EMU
_INCH = 914400


def _rect(
    width_emu: int,
    height_emu: int,
    *,
    x_emu: int = 0,
    y_emu: int = 0,
    fill: str | None = "00FF00",
    outline: ShapeOutline | None = None,
    label: ShapeLabel | None = None,
) -> FigureShape:
    return FigureShape(
        preset="rect",
        x_emu=x_emu,
        y_emu=y_emu,
        width_emu=width_emu,
        height_emu=height_emu,
        fill=fill,
        outline=outline,
        label=label,
    )


def _dark_label(text: str) -> ShapeLabel:
    run = LabelRun(text=text, size_pt=24.0, color="000000", bold=True)
    return ShapeLabel(paragraphs=(LabelParagraph(runs=(run,)),), anchor="ctr")


def _render(figure: ShapeFigure) -> Image.Image:
    image = Image.open(io.BytesIO(draw_shape_figure(figure, anchor="body:0001")))
    image.load()
    return image.convert("RGB")


def test_later_opaque_shape_covers_an_earlier_shapes_label() -> None:
    size = 200 * _PX, 120 * _PX
    labelled = _rect(*size, fill="FFFF00", label=_dark_label("HIDDEN"))
    plain = _rect(*size, fill="FFFF00")
    cover = _rect(*size, fill="00FF00")

    covered = _render(ShapeFigure(size[0], size[1], (labelled, cover)))
    control = _render(ShapeFigure(size[0], size[1], (plain, cover)))

    assert covered.size == control.size
    assert ImageChops.difference(covered, control).getbbox() is None


def test_a_label_still_paints_over_its_own_shape_and_hides_nothing_before_it() -> None:
    size = 200 * _PX, 120 * _PX
    labelled = _rect(*size, fill="FFFF00", label=_dark_label("SHOWN"))
    plain = _rect(*size, fill="FFFF00")

    shown = _render(ShapeFigure(size[0], size[1], (labelled,)))
    control = _render(ShapeFigure(size[0], size[1], (plain,)))

    assert ImageChops.difference(shown, control).getbbox() is not None


@pytest.fixture
def rasterized(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def sentinel(page: str, *, anchor: str) -> bytes:
        calls.append(anchor)
        raise AssertionError("an oversized page must not reach the rasterizer")

    monkeypatch.setattr(drawing, "cropped_page_png", sentinel)
    return calls


def _assert_refused(figure: ShapeFigure, calls: list[str]) -> None:
    with pytest.raises(UnsupportedShapeFigure) as refused:
        draw_shape_figure(figure, anchor="body:0001")
    assert "px" in refused.value.reason
    assert calls == []


def test_a_huge_extent_is_refused_before_rasterizing(rasterized: list[str]) -> None:
    _assert_refused(ShapeFigure(914400000, 914400000, (_rect(_INCH, _INCH),)), rasterized)


def test_a_far_child_shape_is_refused_before_rasterizing(rasterized: list[str]) -> None:
    far = _rect(_INCH, _INCH, x_emu=900000000)
    _assert_refused(ShapeFigure(_INCH, _INCH, (far,)), rasterized)


def test_a_huge_outline_width_is_refused_before_rasterizing(rasterized: list[str]) -> None:
    thick = _rect(_INCH, _INCH, outline=ShapeOutline(color="000000", width_emu=914400000))
    _assert_refused(ShapeFigure(_INCH, _INCH, (thick,)), rasterized)


def test_a_normal_two_inch_figure_still_renders() -> None:
    figure = ShapeFigure(2 * _INCH, 2 * _INCH, (_rect(2 * _INCH, 2 * _INCH),))
    image = _render(figure)
    assert image.width > 0 and image.height > 0
