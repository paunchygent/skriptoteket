"""Maps group coordinates of a Word shape drawing into its figure (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    ``ShapeMapping`` maps child coordinates to figure coordinates and ``ShapeMapping.place``
    returns one shape's box, rotation and mirrors in the figure (``ShapePlacement``).

    Coordinates. The figure box is ``wp:extent``. A single shape takes the size of its own
    ``a:xfrm/a:ext`` and is centred in the box (its ``off`` is ignored): Word sizes ``wp:extent``
    to the rotated bounding box, so a rotated shape is smaller than the box, and an ``a:ext``
    equal to the extent fills it. A group maps its child space onto the parent as
    ``x_parent = off.x + (x - chOff.x) * ext.cx / chExt.cx`` (the same for y); nested groups
    compose their mappings. The top-level group, like a single shape, keeps the size of its own
    ``a:ext`` and is centred in the figure box. A canvas child is already in EMU of the box.

    Group transforms. A group maps its child space into its box (the scale above), mirrors inside
    the box (``flipH``, ``flipV``), then rotates clockwise about the box centre. A child's box
    centre goes through that mapping; the child's size follows the group scale. The child's
    orientation composes in the same order: a mirrored group negates the child's rotation and
    toggles its flip, then the group rotation adds. A child whose result is not a rotated
    rectangle (an uneven group scale applied after a rotation that is not a quarter turn) is a
    shear, which the figure model cannot hold, and raises ``UnsupportedShapeFigure``.

Relationships:
    - ``exam_workspace_docx_shape_reader`` builds one mapping per group and places every shape.
    - ``exam_workspace_docx_shape_xml`` holds the namespaces and the exact XML helpers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_xml import (  # noqa: E501
    DRAWINGML_NS,
    EXT_LST,
    WORD_GROUP_NS,
    Element,
    flag,
    int_attr,
    int_attr_or,
    only,
    unsupported,
)

_Matrix = tuple[float, float, float, float]  # row major: (a, b, c, d) is [[a, b], [c, d]]
_SHEAR_TOLERANCE = 1e-9
_QUARTER_TURNS = {0.0: (1.0, 0.0), 90.0: (0.0, 1.0), 180.0: (-1.0, 0.0), 270.0: (0.0, -1.0)}


def wrap_degrees(degrees: float) -> float:
    """Degrees in [0, 360); a float residue next to 0 or 360 is a whole turn."""
    wrapped = degrees % 360
    return 0.0 if wrapped < _SHEAR_TOLERANCE or 360 - wrapped < _SHEAR_TOLERANCE else wrapped


def _rotation_matrix(degrees: float) -> _Matrix:
    """The clockwise rotation (y points down), exact at quarter turns."""
    cos, sin = _QUARTER_TURNS.get(degrees) or (
        math.cos(math.radians(degrees)),
        math.sin(math.radians(degrees)),
    )
    return cos, -sin, sin, cos


def _multiply(left: _Matrix, right: _Matrix) -> _Matrix:
    return (
        left[0] * right[0] + left[1] * right[2],
        left[0] * right[1] + left[1] * right[3],
        left[2] * right[0] + left[3] * right[2],
        left[2] * right[1] + left[3] * right[3],
    )


def _apply(matrix: _Matrix, x: float, y: float) -> tuple[float, float]:
    return matrix[0] * x + matrix[1] * y, matrix[2] * x + matrix[3] * y


@dataclass(frozen=True)
class ShapePlacement:
    """A shape's box in figure coordinates; ``x`` and ``y`` are the box's top left corner."""

    x: float
    y: float
    width: float
    height: float
    rotation: float
    flip_h: bool
    flip_v: bool


@dataclass(frozen=True)
class ShapeMapping:
    """Child coordinates to figure coordinates: ``figure = linear * child + offset``.

    ``linear`` is rotation, mirror and scale of the groups from the outside in. ``turn``,
    ``mirror_h`` and ``mirror_v`` are the same groups' rotation and mirrors without the scale: the
    orientation ``rotate(turn) * mirror`` that a child's own orientation follows.
    """

    linear: _Matrix = (1.0, 0.0, 0.0, 1.0)
    offset_x: float = 0.0
    offset_y: float = 0.0
    turn: float = 0.0
    mirror_h: bool = False
    mirror_v: bool = False

    def nested(self, group: Element, *, box: tuple[int, int] | None) -> ShapeMapping:
        """Return the mapping of a group's children, composed inside this mapping.

        ``box`` is the figure box for the top-level group, which keeps its own ``ext`` and is
        centred in it instead of using its own ``off``.
        """
        properties = group.find(f"{WORD_GROUP_NS}grpSpPr")
        children = (
            []
            if properties is None
            else only(properties, frozenset({f"{DRAWINGML_NS}xfrm", EXT_LST}))
        )
        transform = next((c for c in children if c.tag == f"{DRAWINGML_NS}xfrm"), None)
        if transform is None:
            raise unsupported("group without a:xfrm")
        off, ext, ch_off, ch_ext = (
            transform.find(f"{DRAWINGML_NS}{name}") for name in ("off", "ext", "chOff", "chExt")
        )
        if off is None or ext is None or ch_off is None or ch_ext is None:
            raise unsupported("group a:xfrm without off, ext, chOff and chExt")
        child_width, child_height = int_attr(ch_ext, "cx"), int_attr(ch_ext, "cy")
        if child_width <= 0 or child_height <= 0:
            raise unsupported("group with an empty a:chExt")
        width, height = int_attr(ext, "cx"), int_attr(ext, "cy")
        if box is None:
            off_x, off_y = float(int_attr(off, "x")), float(int_attr(off, "y"))
        else:
            off_x, off_y = (box[0] - width) / 2, (box[1] - height) / 2
        factor_x, factor_y = width / child_width, height / child_height
        rotation = wrap_degrees(int_attr_or(transform, "rot", 0) / 60000)
        flip_h, flip_v = flag(transform, "flipH"), flag(transform, "flipV")

        # child -> group box (scale), mirror about the box centre, rotate about the box centre.
        mirror: _Matrix = (-1.0 if flip_h else 1.0, 0.0, 0.0, -1.0 if flip_v else 1.0)
        turn_and_mirror = _multiply(_rotation_matrix(rotation), mirror)
        centre_x, centre_y = off_x + width / 2, off_y + height / 2
        shift_x, shift_y = _apply(
            turn_and_mirror,
            off_x - centre_x - factor_x * int_attr(ch_off, "x"),
            off_y - centre_y - factor_y * int_attr(ch_off, "y"),
        )
        group_linear = _multiply(turn_and_mirror, (factor_x, 0.0, 0.0, factor_y))
        outer_x, outer_y = _apply(self.linear, centre_x + shift_x, centre_y + shift_y)
        return ShapeMapping(
            _multiply(self.linear, group_linear),
            outer_x + self.offset_x,
            outer_y + self.offset_y,
            *self._compose_orientation(rotation, flip_h, flip_v),
        )

    def _compose_orientation(
        self, rotation: float, flip_h: bool, flip_v: bool
    ) -> tuple[float, bool, bool]:
        """Orientation of ``rotate(turn) * mirror`` followed by ``rotate(rotation) * flips``.

        One mirror axis reverses the direction of the rotation that follows it; two mirrors are
        a half turn, which commutes.
        """
        reversed_turn = self.mirror_h != self.mirror_v
        turn = self.turn + (-rotation if reversed_turn else rotation)
        return wrap_degrees(turn), self.mirror_h != flip_h, self.mirror_v != flip_v

    def place(
        self,
        *,
        centre: tuple[float, float],
        size: tuple[float, float],
        rotation: float,
        flip_h: bool,
        flip_v: bool,
    ) -> ShapePlacement:
        """Return the box of a shape of ``size`` centred on ``centre`` in child coordinates.

        The shape's own rotation and mirror come first, then the groups'. A shape that the
        groups' scale shears (the result is not a rotated rectangle) is unsupported.
        """
        own_mirror: _Matrix = (-1.0 if flip_h else 1.0, 0.0, 0.0, -1.0 if flip_v else 1.0)
        a, b, c, d = _multiply(self.linear, _multiply(_rotation_matrix(rotation), own_mirror))
        width_scale, height_scale = math.hypot(a, c), math.hypot(b, d)
        if abs(a * b + c * d) > _SHEAR_TOLERANCE * width_scale * height_scale:
            raise unsupported("rotated shape in a group scaled unevenly in x and y")
        centre_x, centre_y = _apply(self.linear, *centre)
        centre_x, centre_y = centre_x + self.offset_x, centre_y + self.offset_y
        width, height = size[0] * width_scale, size[1] * height_scale
        turn, mirror_h, mirror_v = self._compose_orientation(rotation, flip_h, flip_v)
        return ShapePlacement(
            centre_x - width / 2, centre_y - height / 2, width, height, turn, mirror_h, mirror_v
        )


__all__ = ["ShapeMapping", "ShapePlacement", "wrap_degrees"]
