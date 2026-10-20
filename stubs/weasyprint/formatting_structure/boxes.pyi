from __future__ import annotations

from collections.abc import Mapping, Sequence
from xml.etree.ElementTree import Element

class Box:
    element_tag: str
    element: Element | None
    children: Sequence[Box]
    width: float
    margin_left: float
    margin_top: float
    style: Mapping[str, object]
    def content_box_x(self) -> float: ...
    def content_box_y(self) -> float: ...

class TextBox(Box):
    text: str
