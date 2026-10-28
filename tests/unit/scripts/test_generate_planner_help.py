"""Planner help generator tests.

Domain purpose:
    The Klassrumskartan help panel is generated from the getting-started guide.
    Thematic breaks and video annotations in the guide must never reach the
    rendered help, whichever Markdown form the formatter writes them in.

Relationships:
    - Calls `scripts.generate_planner_help._strip_annotations` directly.
"""

from __future__ import annotations

import pytest

from scripts.generate_planner_help import _strip_annotations


@pytest.mark.parametrize("rule", ["---", "___", "***", "_" * 70])
def test_strip_annotations_removes_every_thematic_break_form(rule: str) -> None:
    md = f"Före\n\n{rule}\n\n## Steg 2\n\nEfter"

    stripped = _strip_annotations(md)

    assert rule not in stripped
    assert stripped == "Före\n\n## Steg 2\n\nEfter"


def test_strip_annotations_removes_video_annotations() -> None:
    md = '1. Spara.\n\n[VISA: spara]\n\n> TALMANUS: "Jag sparar."\n> Klart.\n\n[PAUS]\n'

    assert _strip_annotations(md) == "1. Spara."
