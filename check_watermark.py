"""Inspect classroom-planner PDF footer watermark positions.

Relationships:
- Reads repo-generated preview/export PDFs to verify the shared footer watermark placement.
- Complements the classroom-planner PDF branding/rendering checks during local iteration.
"""

from __future__ import annotations

import sys

from pypdf import PdfReader

POINTS_PER_MM = 2.83465


def check_pdf(filename: str) -> None:
    """Print watermark positions for the first page of a PDF."""

    reader = PdfReader(filename)
    page = reader.pages[0]
    text_instances: list[tuple[str, float, float]] = []

    def extract_text(
        text: str,
        _cm: object,
        tm: list[float],
        _font_dict: object,
        _font_size: float,
    ) -> None:
        if "skriptoteket.hule.education" in text:
            text_instances.append((text, tm[4], tm[5]))

    page.extract_text(visitor_text=extract_text)
    page_width_mm = float(page.mediabox.width) / POINTS_PER_MM
    page_height_mm = float(page.mediabox.height) / POINTS_PER_MM

    print(f"{filename}:")
    for text, x, y in text_instances:
        x_mm = x / POINTS_PER_MM
        y_mm = y / POINTS_PER_MM
        right_mm = page_width_mm - x_mm

        print(f"  Text: '{text}'")
        print(f"  Bottom edge (y): {y_mm:.2f} mm")
        print(f"  Right distance (from left edge): {x_mm:.2f} mm")
        print(f"  Right distance (from right edge): {right_mm:.2f} mm")
        print(f"  Page size: {page_width_mm:.2f}x{page_height_mm:.2f} mm")


def main(argv: list[str]) -> int:
    """Run the watermark inspector for the given PDF paths."""

    for filename in argv[1:]:
        check_pdf(filename)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
