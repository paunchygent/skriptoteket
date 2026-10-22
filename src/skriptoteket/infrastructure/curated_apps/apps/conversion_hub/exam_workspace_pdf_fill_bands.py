"""Read one compound even-odd fill as the bands it actually paints (TASK-SKRIPT-39-10-02).

A bordered ``div`` is painted by WeasyPrint as one operation painting two nested
rectangles with the even-odd rule (``re re f*``): the ink is only the bands of the
outer rectangle minus the inner one, an answer line. pdfminer splits every multi-subpath
paint into separate filled objects, so the reader would see two full-height rects and
make a picture. Two fills in separate paint operations stay a solid filled figure: only
a fill whose nested rectangles are painted by ONE operation reads as its bands.

Relationships:
    ``exam_workspace_pdf_layout`` asks for one page's compound fills before calling
    ``exam_workspace_pdf_page_adapter``; the adapter replaces a filled rect matching a
    recorded rectangle with its fill's bands. Boxes are pdfplumber page coordinates
    (x0, top, x1, bottom, top-left origin), converted from pypdf user space through the
    operator's current transformation matrix the way pdfplumber maps device points:
    x unchanged, top is the page height minus the device y.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_graphics import (  # noqa: E501
    Box,
)

if TYPE_CHECKING:
    from pypdf import PageObject

_Corners = tuple[
    tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]
]  # four user-space corners in path order

# An even-odd fill paints the bands of nested rectangles; any other paint operator ends
# the current path without recording a fill.
_EVEN_ODD_PAINT = ("f*", "B*", "b*")
_PATH_END = ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n")
# A band thinner than this in either direction is a shared edge, not ink.
_MIN_BAND_POINTS = 0.01
# A filled rect matches a recorded rectangle this closely per edge.
_MATCH_POINTS = 0.1


@dataclass(frozen=True)
class CompoundFill:
    """One even-odd fill of two nested rectangles: the rectangles and their bands."""

    rects: tuple[Box, Box]
    bands: tuple[Box, ...]


def _floats(values: object) -> tuple[float, ...] | None:
    """Numeric PDF operands as floats, or None when any operand is not a number."""
    if not isinstance(values, (list, tuple)):
        return None
    found: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        found.append(float(value))
    return tuple(found)


def _operator_name(operator: object) -> str:
    if isinstance(operator, bytes):
        return operator.decode("latin-1")
    if isinstance(operator, str):
        return operator
    return ""


def _device_point(
    point: tuple[float, float], matrix: tuple[float, float, float, float, float, float]
) -> tuple[float, float]:
    x, y = point
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def _user_box_to_page(
    corners: _Corners,
    matrix: tuple[float, float, float, float, float, float],
    height: float,
) -> Box:
    """Four user-space corners through the CTM into pdfplumber page coordinates."""
    device = [_device_point(point, matrix) for point in corners]
    top = height - max(point[1] for point in device)
    bottom = height - min(point[1] for point in device)
    return (
        min(point[0] for point in device),
        top,
        max(point[0] for point in device),
        bottom,
    )


def _is_axis_rectangle(points: Sequence[tuple[float, float]]) -> bool:
    """Four points forming an axis-aligned rectangle in path order."""
    if len(points) != 4:
        return False
    if len({point[0] for point in points}) != 2 or len({point[1] for point in points}) != 2:
        return False
    for first, second in zip(points, (*points[1:], points[0]), strict=True):
        if first[0] != second[0] and first[1] != second[1]:
            return False
    return True


def _inside(inner: Box, outer: Box) -> bool:
    """One box inside another, shared edges allowed (a band may start flush)."""
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _bands(outer: Box, inner: Box) -> tuple[Box, ...]:
    """The outer rectangle minus the inner one as top, bottom, left and right strips."""
    candidates = (
        (outer[0], outer[1], outer[2], inner[1]),
        (outer[0], inner[3], outer[2], outer[3]),
        (outer[0], inner[1], inner[0], inner[3]),
        (inner[2], inner[1], outer[2], inner[3]),
    )
    return tuple(
        band
        for band in candidates
        if band[2] - band[0] >= _MIN_BAND_POINTS and band[3] - band[1] >= _MIN_BAND_POINTS
    )


class _FillReader:
    """The content-stream visitor state: subpaths built since the last paint operator."""

    def __init__(self, height: float) -> None:
        self._height = height
        self.fills: list[CompoundFill] = []
        self._rects: list[_Corners] = []
        self._loops: list[_Corners] = []
        self._points: list[tuple[float, float]] = []
        self._closed = False
        self._failed = False

    def visit(
        self, operator: object, operands: object, matrix: object, _text_matrix: object
    ) -> None:
        name = _operator_name(operator)
        if name == "re":
            self._append_re(_floats(operands))
        elif name == "m":
            self._append_move(_floats(operands))
        elif name == "l":
            self._append_line(_floats(operands))
        elif name == "h":
            self._closed = True
        elif name in ("c", "v", "y"):
            self._failed = True
        elif name in _PATH_END:
            self._paint(name, _floats(matrix))
        # Every other operation (text, state, colour, clipping) is ignored.

    def _append_re(self, values: tuple[float, ...] | None) -> None:
        if values is None or len(values) != 4 or values[2] == 0 or values[3] == 0:
            self._failed = True
            return
        x, y, width, height = values
        self._rects.append(((x, y), (x + width, y), (x + width, y + height), (x, y + height)))

    def _append_move(self, values: tuple[float, ...] | None) -> None:
        if values is None or len(values) != 2:
            self._failed = True
            return
        if self._points or self._closed:
            points = self._points
            if self._closed and len(points) == 4 and _is_axis_rectangle(points):
                self._loops.append((points[0], points[1], points[2], points[3]))
            else:
                self._failed = True
        self._points = [(values[0], values[1])]
        self._closed = False

    def _append_line(self, values: tuple[float, ...] | None) -> None:
        if values is None or len(values) != 2 or not self._points:
            self._failed = True
            return
        self._points.append((values[0], values[1]))

    def _paint(self, name: str, matrix: tuple[float, ...] | None) -> None:
        corners = [*self._rects, *self._loops]
        if self._points or self._closed:
            points = self._points
            if self._closed and len(points) == 4 and _is_axis_rectangle(points):
                corners.append((points[0], points[1], points[2], points[3]))
            else:
                corners = []
        if (
            not self._failed
            and name in _EVEN_ODD_PAINT
            and matrix is not None
            and len(matrix) == 6
            and len(corners) == 2
        ):
            full = (matrix[0], matrix[1], matrix[2], matrix[3], matrix[4], matrix[5])
            self._record([_user_box_to_page(pair, full, self._height) for pair in corners])
        self._rects = []
        self._loops = []
        self._points = []
        self._closed = False
        self._failed = False

    def _record(self, boxes: list[Box]) -> None:
        if len(boxes) != 2 or boxes[0] == boxes[1]:
            return
        outer, inner = (
            (boxes[0], boxes[1])
            if _inside(boxes[1], boxes[0])
            else ((boxes[1], boxes[0]) if _inside(boxes[0], boxes[1]) else (None, None))
        )
        if outer is None or inner is None:
            return
        bands = _bands(outer, inner)
        if bands:
            self.fills.append(CompoundFill(rects=(boxes[0], boxes[1]), bands=bands))


def compound_fills(page: PageObject, height: float) -> tuple[CompoundFill, ...]:
    """One pypdf page's compound even-odd fills in pdfplumber page coordinates."""
    reader = _FillReader(height)
    page.extract_text(visitor_operand_before=reader.visit)
    return tuple(reader.fills)


def matches(recorded: Box, seen: Box) -> bool:
    """A filled pdfplumber rect box matching a recorded rectangle per edge."""
    return all(abs(edge - want) <= _MATCH_POINTS for edge, want in zip(recorded, seen, strict=True))


def nested(first: Box, second: Box) -> bool:
    """Two different boxes, one inside the other."""
    return first != second and (_inside(first, second) or _inside(second, first))
