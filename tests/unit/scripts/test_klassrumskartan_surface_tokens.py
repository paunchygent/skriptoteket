"""Klassrumskartan surface-token regression tests.

These tests guard CSS-only workspace surfaces that Vue unit tests cannot inspect
directly. They keep floating sheets and shared popover primitives on opaque
tokens while allowing in-page planner panels to keep their normal panel styling.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PHONE_WORKSPACE_CSS = (
    REPO_ROOT / "frontend/apps/skriptoteket/src/assets/klassrumskartan-phone-workspace.css"
)


def test_phone_workspace_sheet_uses_opaque_modal_surface() -> None:
    css = PHONE_WORKSPACE_CSS.read_text(encoding="utf-8")

    match = re.search(r"\.planner-phone-mode-sheet\s*\{(?P<body>[^}]*)\}", css)

    assert match is not None
    assert "background-color: var(--surface-modal);" in match.group("body")
    assert "background-color: var(--huleedu-panel);" not in match.group("body")
