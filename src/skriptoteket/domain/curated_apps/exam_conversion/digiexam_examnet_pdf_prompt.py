"""Exam.net PDF renderer prompt HTML check.

Purpose:
    Report whether DigiExam prompt HTML carries renderable content (text or
    an image) for the native-exam PDF export path.

Relationships:
    - Used by the workspace native-exam PDF export before item sections are
      assembled.
"""

from __future__ import annotations

import re


def prompt_has_renderable_content(prompt_html: str) -> bool:
    """Return whether prompt HTML contains text or an image."""

    return bool(re.search(r"<img\b|[A-Za-z0-9ÅÄÖåäö]", prompt_html))
