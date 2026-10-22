"""One compound even-odd fill in a single paint operation is its painted bands."""

from __future__ import annotations

import io

import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, FloatObject

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_fill_bands import (  # noqa: E501
    CompoundFill,
    compound_fills,
)

_WIDTH = 595.0
_HEIGHT = 842.0


def _page_with_ops(ops: bytes) -> tuple[bytes, float]:
    """PDF bytes whose single page paints ``ops`` on an A4 page from a zero origin."""
    writer = PdfWriter()
    page = writer.add_page(PdfReader(io.BytesIO(_blank_base())).pages[0])
    stream = DecodedStreamObject()
    stream.set_data(ops)
    page.replace_contents(ArrayObject([stream]))
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue(), _HEIGHT


def _blank_base() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=_WIDTH, height=_HEIGHT)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _fills(data: bytes, height: float) -> tuple[CompoundFill, ...]:
    return compound_fills(PdfReader(io.BytesIO(data)).pages[0], height)


def test_compound_re_re_fill_records_bands_in_page_coordinates() -> None:
    data, height = _page_with_ops(b"100 500 200 80 re 100 501 200 79 re f*")

    assert _fills(data, height) == (
        CompoundFill(
            rects=((100.0, 262.0, 300.0, 342.0), (100.0, 262.0, 300.0, 341.0)),
            bands=((100.0, 341.0, 300.0, 342.0),),
        ),
    )


def test_path_rectangle_compound_fill_records_bands() -> None:
    data, height = _page_with_ops(
        b"100 500 m 300 500 l 300 580 l 100 580 l h 100 501 m 300 501 l 300 580 l 100 580 l h f*"
    )

    assert _fills(data, height) == (
        CompoundFill(
            rects=((100.0, 262.0, 300.0, 342.0), (100.0, 262.0, 300.0, 341.0)),
            bands=((100.0, 341.0, 300.0, 342.0),),
        ),
    )


def test_two_separate_fills_record_nothing() -> None:
    data, height = _page_with_ops(b"100 500 200 80 re f* 100 501 200 79 re f*")

    assert _fills(data, height) == ()


def test_evenodd_fill_of_non_nested_rects_records_nothing() -> None:
    data, height = _page_with_ops(b"100 500 50 50 re 400 500 50 50 re f*")

    assert _fills(data, height) == ()


def test_nonzero_winding_fill_of_nested_rects_records_nothing() -> None:
    data, height = _page_with_ops(b"100 500 200 80 re 100 501 200 79 re f")

    assert _fills(data, height) == ()


def test_nonzero_mediabox_origin_matches_pdfplumber_rects() -> None:
    writer = PdfWriter()
    page = writer.add_page(PdfReader(io.BytesIO(_blank_base())).pages[0])
    page.mediabox = ArrayObject(
        [FloatObject(10), FloatObject(20), FloatObject(_WIDTH + 10), FloatObject(_HEIGHT + 20)]
    )
    stream = DecodedStreamObject()
    stream.set_data(b"100 500 200 80 re 100 501 200 79 re f*")
    page.replace_contents(ArrayObject([stream]))
    output = io.BytesIO()
    writer.write(output)
    data = output.getvalue()

    (fill,) = _fills(data, _HEIGHT)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        boxes = [
            (rect["x0"], rect["top"], rect["x1"], rect["bottom"]) for rect in pdf.pages[0].rects
        ]
    assert len(boxes) == 2
    for recorded in fill.rects:
        assert any(
            all(abs(edge - seen) <= 0.1 for edge, seen in zip(recorded, box, strict=True))
            for box in boxes
        )
