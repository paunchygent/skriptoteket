"""Shared print primitives for Klassrumskartan PDF renderers.

Purpose:
    Keep tiny presentation helpers shared between the seating and grouping PDF
    renderers so workspace exports and share-link PDF downloads inherit the
    same print-owned visual language without depending on responsive share
    page HTML.

Relationships:
    - Consumed by `poster_renderer.py` for circular seating labels.
    - Consumed by `grouping_pdf_renderer.py` for numbered member markers.
"""

from __future__ import annotations


def split_print_student_label(value: str) -> tuple[str, str]:
    """Split a compact student label into two print-safe centered lines."""

    words = [word for word in value.replace("-", " ").split() if word]
    if not words:
        return value, ""
    if len(words) == 1:
        return words[0], ""
    return words[0], words[-1]


def grouping_member_count_text(member_count: int) -> str:
    """Return Swedish count text for one grouping PDF card."""

    if member_count == 1:
        return "1 elev"
    return f"{member_count} elever"
