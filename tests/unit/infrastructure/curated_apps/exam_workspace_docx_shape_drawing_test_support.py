"""Shape builders and pixel probes shared by the Word shape drawer's pixel tests."""

from __future__ import annotations

import io

from PIL import Image

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_drawing import (  # noqa: E501
    draw_shape_figure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    FigureShape,
    PresetGeometry,
    ShapeFigure,
    ShapeLabel,
    ShapeOutline,
)

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
    rotation_deg: float = 0.0,
    flip_h: bool = False,
    flip_v: bool = False,
    adjustments: tuple[tuple[str, int], ...] = (),
    label: ShapeLabel | None = None,
) -> FigureShape:
    return FigureShape(
        preset=preset,
        x_emu=x_px * _PX,
        y_emu=y_px * _PX,
        width_emu=width_px * _PX,
        height_emu=height_px * _PX,
        rotation_deg=rotation_deg,
        flip_h=flip_h,
        flip_v=flip_v,
        adjustments=adjustments,
        fill=fill,
        outline=outline,
        label=label,
    )


def _figure(*shapes: FigureShape, width_px: int = 200, height_px: int = 120) -> ShapeFigure:
    return ShapeFigure(width_px * _PX, height_px * _PX, tuple(shapes))


def _draw(figure: ShapeFigure) -> Image.Image:
    content = draw_shape_figure(figure, anchor="body:0001")
    image = Image.open(io.BytesIO(content))
    image.load()
    assert image.format == "PNG"
    return image.convert("RGB")


def _pixel(image: Image.Image, x: int, y: int) -> tuple[int, int, int]:
    """The RGB pixel at ``x``, ``y`` of a drawn image."""
    pixel = image.getpixel((x, y))
    assert isinstance(pixel, tuple)
    return pixel[0], pixel[1], pixel[2]


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
    return _pixel(image, x, y)


def _column_ink(image: Image.Image, box: Box, fx: float) -> int:
    left, top, right, bottom = box
    x = min(right - 1, round(left + fx * (right - left)))
    return sum(_is_ink(_pixel(image, x, y)) for y in range(top, bottom))


def _row_ink(image: Image.Image, box: Box, fy: float) -> int:
    left, top, right, bottom = box
    y = min(bottom - 1, round(top + fy * (bottom - top)))
    return sum(_is_ink(_pixel(image, x, y)) for x in range(left, right))


def _transitions(image: Image.Image, box: Box, fy: float) -> int:
    left, top, right, bottom = box
    y = round(top + fy * (bottom - top))
    states = [_is_ink(_pixel(image, x, y)) for x in range(left, right)]
    return sum(1 for a, b in zip(states, states[1:], strict=False) if a != b)


def _is_red(pixel: tuple[int, int, int]) -> bool:
    return pixel[0] > 200 and pixel[1] < 60 and pixel[2] < 60


def _is_white(pixel: tuple[int, int, int]) -> bool:
    return min(pixel) > 245


def _is_dark(pixel: tuple[int, int, int]) -> bool:
    return max(pixel) < 100
