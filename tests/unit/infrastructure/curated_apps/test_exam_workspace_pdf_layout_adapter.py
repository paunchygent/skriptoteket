"""The PDF layout adapter narrows pdfplumber records into typed geometry (R7/F7)."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_layout import (  # noqa: E501
    PdfLayoutError,
    _object_box,
    _visible,
)


def test_object_box_reads_ints_and_floats() -> None:
    assert _object_box({"x0": 1, "top": 2, "x1": 3.5, "bottom": 4}) == (1.0, 2.0, 3.5, 4.0)


def test_object_box_missing_key_names_it() -> None:
    with pytest.raises(PdfLayoutError, match="bottom"):
        _object_box({"x0": 1, "top": 2, "x1": 3})


def test_object_box_string_value_names_it() -> None:
    with pytest.raises(PdfLayoutError, match="x0"):
        _object_box({"x0": "12", "top": 2, "x1": 3, "bottom": 4})


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (None, True),
        (1, False),
        ((1, 1, 1), False),
        ((0, 0, 0, 0), False),
        ((0.2,), True),
        ("pattern", True),
    ],
)
def test_visible_table(color: object, expected: bool) -> None:
    assert _visible(color) is expected
