"""Draws a Word shape figure as a PNG (TASK-SKRIPT-39-04-22, D1).

Purpose:
    The Word import shows a drawing made of Word shapes as a picture. This module draws
    one ``ShapeFigure`` the way Word does: it computes each preset shape's outline from the
    ECMA-376 preset shape definitions (box, adjustment guides, flips, rotation), paints fill,
    outline, dashes and arrowheads as inline SVG, lays each shape's wrapped label text over
    it as HTML, prints that page with WeasyPrint and rasterizes it through the shared PDFium
    gate. The page is as large as the figure's shapes and strokes need, so nothing that
    reaches past the drawing's extent is clipped.

Relationships:
    - Reads the model of ``exam_workspace_docx_shape_figure``.
    - Prints and crops through ``cropped_page_png`` of ``exam_workspace_labeler_block_image``
      and raises its ``LabelerSourceImageUnavailable`` when the figure draws nothing.
    - ``exam_workspace_docx_chunker`` calls ``draw_shape_figure`` for each shape drawing.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    LINE_PRESETS,
    Arrowhead,
    ArrowheadSize,
    DashStyle,
    FigureShape,
    LabelParagraph,
    LabelRun,
    ShapeFigure,
    ShapeOutline,
    UnsupportedShapeFigure,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    cropped_page_png,
)

Point = tuple[float, float]
Rect = tuple[float, float, float, float]  # left, top, right, bottom

_EMU_PER_PX = 9525
_MIN_STROKE_PX = 0.5
_MIN_ARROWHEAD_PX = 4.0
_ARROWHEAD_FACTOR: dict[ArrowheadSize, float] = {"sm": 2.0, "med": 3.0, "lg": 5.0}
# Dash and gap lengths, in stroke widths, as DrawingML's preset dashes define them.
_DASHES: dict[DashStyle, tuple[float, ...]] = {
    "solid": (),
    "dash": (4, 3),
    "sysDash": (3, 1),
    "dot": (1, 3),
    "sysDot": (1, 1),
    "lgDash": (8, 3),
    "dashDot": (4, 3, 1, 3),
    "sysDashDot": (3, 1, 1, 1),
}
# Share of a half-axis (an ellipse) or a corner radius (a rounded rectangle) that the shape's
# text box gives up on each side: the box is inscribed at 45 degrees.
_INSCRIBED = 1 - math.cos(math.radians(45))
_PAGE_PADDING_PX = 2.0
# Word's largest page side, 22 inches at 96 px per inch: a bigger drawing is not rasterized.
_MAX_PAGE_SIDE_PX = 22 * 96
_JUSTIFY = {"t": "flex-start", "ctr": "center", "b": "flex-end"}


@dataclass(frozen=True)
class _Outline:
    """A shape's outline in its own box: what to draw and where its label text fits."""

    kind: Literal["rect", "ellipse", "polygon"]
    points: tuple[Point, ...]
    radius: float
    text_rect: Rect


def _px(emu: float) -> float:
    return emu / _EMU_PER_PX


def _n(value: float) -> str:
    return f"{value:.3f}"


def _pin(low: float, value: float, high: float) -> float:
    return max(low, min(value, high))


def draw_shape_figure(figure: ShapeFigure, *, anchor: str) -> bytes:
    """Return a PNG of the figure, cropped to its drawn content.

    Raises:
        UnsupportedShapeFigure: the page the figure needs is larger than Word's largest page.
        LabelerSourceImageUnavailable: the figure draws nothing.
    """
    bounds = _bounds(figure)
    left, top, right, bottom = bounds
    side = max(right - left, bottom - top)
    if not side <= _MAX_PAGE_SIDE_PX:
        raise UnsupportedShapeFigure(
            f"the drawing needs a {side:.0f} px page, over the {_MAX_PAGE_SIDE_PX} px limit"
        )
    return cropped_page_png(_page(figure, bounds), anchor=anchor)


def _page(figure: ShapeFigure, bounds: Rect) -> str:
    left, top, right, bottom = bounds
    width, height = math.ceil(right - left), math.ceil(bottom - top)
    layers = "".join(_shape_layer(shape, left, top, width, height) for shape in figure.shapes)
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        f"@page {{ size: {width}px {height}px; margin: 0 }} "
        "html, body { margin: 0; padding: 0; background: #fff } "
        "body { font-family: sans-serif } "
        "svg { position: absolute; left: 0; top: 0 } "
        "</style></head><body>"
        f'<div style="position:relative;width:{width}px;height:{height}px">'
        f"{layers}</div></body></html>"
    )


def _shape_layer(shape: FigureShape, left: float, top: float, width: int, height: int) -> str:
    """One shape's body and label as the next layer of the page, so DOM order is paint order."""
    body = _shape_svg(shape, left, top)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
        if body
        else ""
    )
    return svg + _label_div(shape, left, top)


def _bounds(figure: ShapeFigure) -> Rect:
    """The page in figure pixels: the extent, every turned shape and the widest stroke."""
    left, top = 0.0, 0.0
    right, bottom = _px(figure.width_emu), _px(figure.height_emu)
    padding = _PAGE_PADDING_PX
    for shape in figure.shapes:
        for x, y in _turned_corners(shape):
            left, top = min(left, x), min(top, y)
            right, bottom = max(right, x), max(bottom, y)
        reach = 0.0
        if shape.outline is not None:
            stroke = _stroke_px(shape.outline)
            reach = stroke / 2 + max(
                (_arrowhead_size(end, stroke)[1] for end in _ends(shape) if end is not None),
                default=0.0,
            )
        padding = max(padding, reach + _PAGE_PADDING_PX)
    return left - padding, top - padding, right + padding, bottom + padding


def _turned_corners(shape: FigureShape) -> tuple[Point, ...]:
    x, y = _px(shape.x_emu), _px(shape.y_emu)
    w, h = _px(shape.width_emu), _px(shape.height_emu)
    cx, cy = x + w / 2, y + h / 2
    angle = math.radians(shape.rotation_deg)
    cos, sin = math.cos(angle), math.sin(angle)
    return tuple(
        (cx + (px - cx) * cos - (py - cy) * sin, cy + (px - cx) * sin + (py - cy) * cos)
        for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))
    )


def _stroke_px(outline: ShapeOutline) -> float:
    return max(_px(outline.width_emu), _MIN_STROKE_PX)


def _ends(shape: FigureShape) -> tuple[Arrowhead | None, Arrowhead | None]:
    """The arrowheads that draw: only a line has path ends."""
    if shape.preset not in LINE_PRESETS or shape.outline is None:
        return None, None
    return shape.outline.head, shape.outline.tail


def _arrowhead_size(head: Arrowhead, stroke: float) -> tuple[float, float]:
    """The head's (width across the line, length along it) in pixels."""
    width = max(_ARROWHEAD_FACTOR[head.width] * stroke, _MIN_ARROWHEAD_PX)
    length = max(_ARROWHEAD_FACTOR[head.length] * stroke, _MIN_ARROWHEAD_PX)
    return width, length


def _guide(shape: FigureShape, name: str, default: float) -> float:
    return float(dict(shape.adjustments).get(name, default))


def _outline(shape: FigureShape, w: float, h: float) -> _Outline:
    """The preset's outline in its box at (0, 0), before flips and rotation."""
    ss = min(w, h)
    box = (0.0, 0.0, w, h)
    preset = shape.preset
    if preset == "rect" or preset in LINE_PRESETS:
        return _Outline("rect", (), 0.0, box)
    if preset == "roundRect":
        radius = ss * _pin(0, _guide(shape, "adj", 16667), 50000) / 100000
        inset = radius * _INSCRIBED
        return _Outline("rect", (), radius, (inset, inset, w - inset, h - inset))
    if preset == "ellipse":
        dx, dy = w / 2 * _INSCRIBED, h / 2 * _INSCRIBED
        return _Outline("ellipse", (), 0.0, (dx, dy, w - dx, h - dy))
    if preset == "triangle":
        apex = w * _pin(0, _guide(shape, "adj", 50000), 100000) / 100000
        points = ((0, h), (apex, 0), (w, h))
        return _Outline("polygon", points, 0.0, (apex / 2, h / 2, apex / 2 + w / 2, h))
    if preset == "rtTriangle":
        return _Outline("polygon", ((0, 0), (0, h), (w, h)), 0.0, box)
    return _block_arrow(shape, w, h)


def _block_arrow(shape: FigureShape, w: float, h: float) -> _Outline:
    ss = min(w, h)
    horizontal = shape.preset in ("rightArrow", "leftArrow")
    a1 = _pin(0, _guide(shape, "adj1", 50000), 100000)
    long_side = w if horizontal else h
    a2 = _pin(0, _guide(shape, "adj2", 50000), 100000 * long_side / ss)
    head = ss * a2 / 100000  # how far the head reaches along the arrow
    cross = h if horizontal else w
    half_shaft = cross * a1 / 200000
    mid = cross / 2
    near, far = mid - half_shaft, mid + half_shaft
    # The text box runs a little into the head, as ECMA-376 defines it.
    reach = near * head / (cross / 2) if cross else 0.0
    points: tuple[Point, ...]
    if shape.preset == "rightArrow":
        x1 = w - head
        points = ((0, near), (x1, near), (x1, 0), (w, mid), (x1, h), (x1, far), (0, far))
        text: Rect = (0, near, x1 + reach, far)
    elif shape.preset == "leftArrow":
        points = ((0, mid), (head, 0), (head, near), (w, near), (w, far), (head, far), (head, h))
        text = (head - reach, near, w, far)
    elif shape.preset == "upArrow":
        points = ((0, head), (mid, 0), (w, head), (far, head), (far, h), (near, h), (near, head))
        text = (near, head - reach, far, h)
    else:
        y1 = h - head
        points = ((0, y1), (near, y1), (near, 0), (far, 0), (far, y1), (w, y1), (mid, h))
        text = (near, 0, far, y1 + reach)
    return _Outline("polygon", points, 0.0, text)


def _flip(shape: FigureShape, point: Point, w: float, h: float) -> Point:
    x, y = point
    return (w - x if shape.flip_h else x, h - y if shape.flip_v else y)


def _paint(shape: FigureShape) -> str:
    fill = "none" if shape.fill is None or shape.preset in LINE_PRESETS else f"#{shape.fill}"
    paint = f'fill="{html.escape(fill)}"'
    outline = shape.outline
    if outline is None:
        return paint + ' stroke="none"'
    stroke = _stroke_px(outline)
    paint += f' stroke="#{html.escape(outline.color)}" stroke-width="{_n(stroke)}"'
    dashes = _DASHES[outline.dash]
    if dashes:
        paint += f' stroke-dasharray="{",".join(_n(d * stroke) for d in dashes)}"'
    return paint + ' stroke-linejoin="miter" stroke-miterlimit="8"'


def _shape_svg(shape: FigureShape, origin_x: float, origin_y: float) -> str:
    x, y = _px(shape.x_emu) - origin_x, _px(shape.y_emu) - origin_y
    w, h = _px(shape.width_emu), _px(shape.height_emu)
    if shape.preset in LINE_PRESETS:
        body = _line_svg(shape, x, y, w, h)
    else:
        body = _closed_svg(shape, x, y, w, h)
    if not body:
        return ""
    if shape.rotation_deg % 360 == 0:
        return body
    turn = f"rotate({_n(shape.rotation_deg)} {_n(x + w / 2)} {_n(y + h / 2)})"
    return f'<g transform="{turn}">{body}</g>'


def _closed_svg(shape: FigureShape, x: float, y: float, w: float, h: float) -> str:
    if shape.fill is None and shape.outline is None:
        return ""
    outline = _outline(shape, w, h)
    paint = _paint(shape)
    if outline.kind == "rect":
        radius = f' rx="{_n(outline.radius)}" ry="{_n(outline.radius)}"' if outline.radius else ""
        return f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}"{radius} {paint}/>'
    if outline.kind == "ellipse":
        return (
            f'<ellipse cx="{_n(x + w / 2)}" cy="{_n(y + h / 2)}" rx="{_n(w / 2)}" '
            f'ry="{_n(h / 2)}" {paint}/>'
        )
    points = " ".join(
        f"{_n(x + px)},{_n(y + py)}"
        for px, py in (_flip(shape, point, w, h) for point in outline.points)
    )
    return f'<polygon points="{points}" {paint}/>'


def _line_svg(shape: FigureShape, x: float, y: float, w: float, h: float) -> str:
    outline = shape.outline
    if outline is None:
        return ""
    start = _flip(shape, (0.0, 0.0), w, h)
    end = _flip(shape, (w, h), w, h)
    start, end = (x + start[0], y + start[1]), (x + end[0], y + end[1])
    stroke = _stroke_px(outline)
    head, tail = outline.head, outline.tail
    heads = ""
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length > 0:
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        line_start, line_end = start, end
        if head is not None:
            heads += _arrowhead_svg(head, start, (-ux, -uy), stroke, outline.color)
            line_start = _shortened(head, start, (ux, uy), stroke, length)
        if tail is not None:
            heads += _arrowhead_svg(tail, end, (ux, uy), stroke, outline.color)
            line_end = _shortened(tail, end, (-ux, -uy), stroke, length)
        start, end = line_start, line_end
    paint = _paint(shape)
    return (
        f'<polyline points="{_n(start[0])},{_n(start[1])} {_n(end[0])},{_n(end[1])}" '
        f"{paint}/>{heads}"
    )


def _shortened(
    head: Arrowhead, tip: Point, inward: Point, stroke: float, line_length: float
) -> Point:
    """Where the line stops under a pointed head, so the stroke does not poke past the tip."""
    share = {"triangle": 0.8, "stealth": 0.5}.get(head.kind, 0.0)
    back = min(_arrowhead_size(head, stroke)[1] * share, line_length / 2)
    return tip[0] + inward[0] * back, tip[1] + inward[1] * back


def _arrowhead_svg(head: Arrowhead, tip: Point, outward: Point, stroke: float, color: str) -> str:
    """One arrowhead at a path end, pointing along ``outward``, as an explicit shape."""
    width, length = _arrowhead_size(head, stroke)
    ox, oy = outward
    nx, ny = -oy, ox  # across the line

    def at(along: float, across: float) -> Point:
        return tip[0] - ox * along + nx * across, tip[1] - oy * along + ny * across

    fill = f'fill="#{html.escape(color)}" stroke="none"'
    if head.kind == "oval":
        centre = at(length / 2, 0)
        angle = math.degrees(math.atan2(oy, ox))
        return (
            f'<ellipse cx="{_n(centre[0])}" cy="{_n(centre[1])}" rx="{_n(length / 2)}" '
            f'ry="{_n(width / 2)}" transform="rotate({_n(angle)} {_n(centre[0])} '
            f'{_n(centre[1])})" {fill}/>'
        )
    points: tuple[Point, ...]
    if head.kind == "diamond":
        points = (at(0, 0), at(length / 2, width / 2), at(length, 0), at(length / 2, -width / 2))
    elif head.kind == "stealth":
        points = (at(0, 0), at(length, width / 2), at(length * 0.7, 0), at(length, -width / 2))
    elif head.kind == "arrow":
        # An open arrowhead: two strokes of the line's width meeting at the tip.
        wing_a, tip_point, wing_b = at(length, width / 2), at(0, 0), at(length, -width / 2)
        text = " ".join(f"{_n(px)},{_n(py)}" for px, py in (wing_a, tip_point, wing_b))
        return (
            f'<polyline points="{text}" fill="none" stroke="#{html.escape(color)}" '
            f'stroke-width="{_n(stroke)}" stroke-linejoin="miter" stroke-miterlimit="8"/>'
        )
    else:
        points = (at(0, 0), at(length, width / 2), at(length, -width / 2))
    text = " ".join(f"{_n(px)},{_n(py)}" for px, py in points)
    return f'<polygon points="{text}" {fill}/>'


def _label_div(shape: FigureShape, origin_x: float, origin_y: float) -> str:
    label = shape.label
    if label is None:
        return ""
    x, y = _px(shape.x_emu) - origin_x, _px(shape.y_emu) - origin_y
    w, h = _px(shape.width_emu), _px(shape.height_emu)
    left, top, right, bottom = _flipped_rect(shape, _outline(shape, w, h).text_rect, w, h)
    padding = (
        _px(label.inset_top_emu) + top,
        _px(label.inset_right_emu) + (w - right),
        _px(label.inset_bottom_emu) + (h - bottom),
        _px(label.inset_left_emu) + left,
    )
    turn = (
        f";transform:rotate({_n(shape.rotation_deg)}deg);transform-origin:50% 50%"
        if shape.rotation_deg % 360
        else ""
    )
    paragraphs = "".join(_paragraph(paragraph) for paragraph in label.paragraphs)
    return (
        f'<div style="position:absolute;box-sizing:border-box;left:{_n(x)}px;top:{_n(y)}px;'
        f"width:{_n(w)}px;height:{_n(h)}px;display:flex;flex-direction:column;"
        f"justify-content:{_JUSTIFY[label.anchor]};"
        f'padding:{" ".join(_n(max(p, 0.0)) + "px" for p in padding)}{turn}">'
        f"{paragraphs}</div>"
    )


def _flipped_rect(shape: FigureShape, rect: Rect, w: float, h: float) -> Rect:
    left, top, right, bottom = rect
    if shape.flip_h:
        left, right = w - right, w - left
    if shape.flip_v:
        top, bottom = h - bottom, h - top
    return left, top, right, bottom


def _paragraph(paragraph: LabelParagraph) -> str:
    runs = "".join(_run(run) for run in paragraph.runs)
    if not any(run.text for run in paragraph.runs):
        size = paragraph.runs[-1].size_pt if paragraph.runs else 11.0
        runs = f'<span style="font-size:{size:g}pt">&#160;</span>'
    return (
        f'<div style="margin:0;white-space:pre-wrap;overflow-wrap:break-word;'
        f'text-align:{paragraph.align}">{runs}</div>'
    )


def _run(run: LabelRun) -> str:
    style = f"font-size:{run.size_pt:g}pt;color:#{html.escape(run.color)}"
    if run.bold:
        style += ";font-weight:bold"
    if run.italic:
        style += ";font-style:italic"
    if run.underline:
        style += ";text-decoration:underline"
    return f'<span style="{style}">{html.escape(run.text)}</span>'
