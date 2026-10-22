"""Every PDFium call is serialized process-wide and returned images survive the lock (R4)."""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from PIL import Image

from skriptoteket.infrastructure.documents import pdfium_access

pytestmark = pytest.mark.unit

_HTML = "<!doctype html><html><body><p>R4 rasterize</p></body></html>"


def test_rasterize_serializes_documents_across_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    a_inside_render = threading.Event()
    release_a = threading.Event()
    b_opened = threading.Event()

    class _Bitmap:
        def to_pil(self) -> Image.Image:
            return Image.new("RGB", (2, 2), "white")

    class _Page:
        def __init__(self, label: str) -> None:
            self._label = label

        def render(self, *, scale: float) -> _Bitmap:
            events.append(f"{self._label}.render")
            if self._label == "A":
                a_inside_render.set()
                release_a.wait(timeout=5)
            return _Bitmap()

    class _Document:
        def __init__(self, pdf: bytes) -> None:
            self._label = pdf.decode()
            events.append(f"{self._label}.open")
            if self._label == "B":
                b_opened.set()

        def __len__(self) -> int:
            return 1

        def __getitem__(self, index: int) -> _Page:
            return _Page(self._label)

        def close(self) -> None:
            events.append(f"{self._label}.close")

    monkeypatch.setattr(pdfium_access, "pypdfium2", SimpleNamespace(PdfDocument=_Document))

    outcomes: dict[str, object] = {}

    def rasterize(label: str) -> None:
        try:
            outcomes[label] = pdfium_access.rasterize_pdf_pages(label.encode(), scale=1.0)
        except BaseException as error:  # noqa: BLE001 - surfaced through the assertion below
            outcomes[label] = error

    thread_a = threading.Thread(target=rasterize, args=("A",))
    thread_b = threading.Thread(target=rasterize, args=("B",))
    thread_a.start()
    assert a_inside_render.wait(timeout=5)
    thread_b.start()
    # While A holds the process-wide lock inside render, B must not open its document.
    assert not b_opened.wait(timeout=0.1)
    release_a.set()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    assert not thread_a.is_alive()
    assert not thread_b.is_alive()
    assert events == ["A.open", "A.render", "A.close", "B.open", "B.render", "B.close"]
    assert all(isinstance(result, tuple) for result in outcomes.values())


def test_render_error_closes_document_and_releases_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _RenderError(Exception):
        pass

    class _Page:
        def render(self, *, scale: float) -> object:
            raise _RenderError

    class _FailingDocument:
        def __init__(self, pdf: bytes) -> None:
            events.append("open")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, index: int) -> _Page:
            return _Page()

        def close(self) -> None:
            events.append("close")

    class _GoodPage:
        def render(self, *, scale: float) -> SimpleNamespace:
            return SimpleNamespace(to_pil=lambda: Image.new("RGB", (2, 2)))

    class _GoodDocument:
        def __len__(self) -> int:
            return 1

        def __getitem__(self, index: int) -> _GoodPage:
            return _GoodPage()

        def close(self) -> None:
            pass

    monkeypatch.setattr(pdfium_access, "pypdfium2", SimpleNamespace(PdfDocument=_FailingDocument))
    with pytest.raises(_RenderError):
        pdfium_access.rasterize_pdf_pages(b"boom", scale=1.0)
    assert events == ["open", "close"]

    # The lock was released: a following call runs to completion.
    monkeypatch.setattr(
        pdfium_access, "pypdfium2", SimpleNamespace(PdfDocument=lambda pdf: _GoodDocument())
    )
    images = pdfium_access.rasterize_pdf_pages(b"ok", scale=1.0)
    assert len(images) == 1


def test_real_pdf_yields_one_usable_image() -> None:
    from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes

    images = pdfium_access.rasterize_pdf_pages(render_html_to_pdf_bytes(html=_HTML), scale=1.0)

    assert len(images) == 1
    image = images[0]
    assert image.size == (596, 842)
    # Pixels stay readable after the document closed and the lock was released.
    image.load()
    assert isinstance(image.convert("L").getpixel((10, 10)), int)


def test_selected_pages_render_alone_in_the_order_asked() -> None:
    from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes

    pdf = render_html_to_pdf_bytes(
        html=(
            "<!doctype html><html><head><style>@page { size: 200pt 100pt; margin: 0 }"
            " section { page-break-after: always; height: 100pt }</style></head><body>"
            '<section style="background: #f00"></section>'
            '<section style="background: #0f0"></section>'
            '<section style="background: #00f"></section></body></html>'
        )
    )

    images = pdfium_access.rasterize_pdf_pages(pdf, scale=1.0, pages=[2, 0])

    assert [image.convert("RGB").getpixel((100, 50)) for image in images] == [
        (0, 0, 255),
        (255, 0, 0),
    ]
