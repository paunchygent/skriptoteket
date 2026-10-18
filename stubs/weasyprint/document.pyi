from __future__ import annotations

from collections.abc import Callable

class Page:
    anchors: dict[str, tuple[float, float]]

class Document:
    pages: list[Page]
    def write_pdf(
        self,
        target: None = None,
        zoom: float = 1,
        finisher: Callable[..., object] | None = None,
        **options: object,
    ) -> bytes: ...
