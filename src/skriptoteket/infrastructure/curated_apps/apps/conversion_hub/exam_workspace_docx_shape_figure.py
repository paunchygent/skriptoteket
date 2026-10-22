"""A figure drawn with Word's shapes, read from DrawingML (TASK-SKRIPT-39-04-22).

Purpose:
    The Word import turns a drawing made of Word shapes into a picture (D1, D2). This
    module holds the figure model between the reader, which reads one ``w:drawing`` into
    a ``ShapeFigure``, and the drawer, which draws that figure as a PNG. Every length is
    in EMU in the figure's own coordinates: (0, 0) is the drawing's top left corner and
    every group and canvas transform is already applied.

Relationships:
    - ``exam_workspace_docx_shape_reader`` builds the figure, or raises
      ``UnsupportedShapeFigure`` when any part of it is outside D2 (D3).
    - ``exam_workspace_docx_shape_drawing`` draws it.
    - ``exam_workspace_docx_chunker`` places the PNG in the drawing chunk (D5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PresetGeometry = Literal[
    "rect",
    "roundRect",
    "ellipse",
    "triangle",
    "rtTriangle",
    "line",
    "straightConnector1",
    "rightArrow",
    "leftArrow",
    "upArrow",
    "downArrow",
]
# Presets drawn as one straight stroke from the box's top left to its bottom right corner
# (before flips); they have no inside to fill.
LINE_PRESETS: frozenset[str] = frozenset({"line", "straightConnector1"})

ArrowheadKind = Literal["triangle", "arrow", "stealth", "oval", "diamond"]
ArrowheadSize = Literal["sm", "med", "lg"]
DashStyle = Literal["solid", "dash", "sysDash", "dot", "sysDot", "lgDash", "dashDot", "sysDashDot"]
LabelAlign = Literal["left", "center", "right", "justify"]
LabelAnchor = Literal["t", "ctr", "b"]


class UnsupportedShapeFigure(Exception):
    """The drawing holds a shape, fill, effect or container outside D2; ``reason`` names it."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Arrowhead:
    """A line end (``a:headEnd`` or ``a:tailEnd``) other than ``none``."""

    kind: ArrowheadKind
    width: ArrowheadSize = "med"
    length: ArrowheadSize = "med"


@dataclass(frozen=True)
class ShapeOutline:
    """A solid outline. ``color`` is six upper-case hex digits, ``width_emu`` the stroke.

    ``head`` sits at the path start and ``tail`` at its end, as DrawingML defines them.
    """

    color: str
    width_emu: int
    dash: DashStyle = "solid"
    head: Arrowhead | None = None
    tail: Arrowhead | None = None


@dataclass(frozen=True)
class LabelRun:
    """One run of label text. ``color`` is six upper-case hex digits."""

    text: str
    size_pt: float
    color: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass(frozen=True)
class LabelParagraph:
    runs: tuple[LabelRun, ...]
    align: LabelAlign = "left"


@dataclass(frozen=True)
class ShapeLabel:
    """A shape's text-box label (``wps:txbx``) with its ``wps:bodyPr`` insets and anchor."""

    paragraphs: tuple[LabelParagraph, ...]
    inset_left_emu: int = 91440
    inset_top_emu: int = 45720
    inset_right_emu: int = 91440
    inset_bottom_emu: int = 45720
    anchor: LabelAnchor = "t"


@dataclass(frozen=True)
class FigureShape:
    """One preset shape at its box in figure coordinates.

    ``rotation_deg`` turns the shape clockwise about its box centre; ``flip_h`` and
    ``flip_v`` mirror it inside its box before the rotation. ``adjustments`` holds the
    ``a:avLst`` guide values (``adj``, ``adj1``, ``adj2``) the source sets; a guide it does
    not set takes the preset's ECMA-376 default. ``fill`` is six upper-case hex digits or
    None for no fill.
    """

    preset: PresetGeometry
    x_emu: float
    y_emu: float
    width_emu: float
    height_emu: float
    rotation_deg: float = 0.0
    flip_h: bool = False
    flip_v: bool = False
    adjustments: tuple[tuple[str, int], ...] = ()
    fill: str | None = None
    outline: ShapeOutline | None = None
    label: ShapeLabel | None = None


@dataclass(frozen=True)
class ShapeFigure:
    """One drawing's shapes in paint order, inside its ``wp:extent`` box."""

    width_emu: int
    height_emu: int
    shapes: tuple[FigureShape, ...]

    @property
    def plain_lines(self) -> bool:
        """Only lines or straight connectors, with no arrowhead and no label (D4)."""
        return all(
            shape.preset in LINE_PRESETS
            and shape.label is None
            and (
                shape.outline is None or (shape.outline.head is None and shape.outline.tail is None)
            )
            for shape in self.shapes
        )
