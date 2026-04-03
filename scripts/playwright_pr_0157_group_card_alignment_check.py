"""Live PR-0157 proof for grouping card header alignment.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


Purpose:
    Verify the live `Grupper` workspace after the header-row cleanup so the
    group-name input and reorder/delete controls share one row, one height
    scale, and no redundant `Gruppnamn` label.

Relationships:
    - reuses shared Klassrumskartan Playwright helpers for login, roster
      creation, and workspace navigation
    - writes a screenshot under `.artifacts/pr-0157-group-card-alignment-check/`
"""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Locator, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    create_roster,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0157-group-card-alignment-check")


def _bounding_box(locator: Locator) -> dict[str, float]:
    """Return a concrete bounding box for an element that must be visible."""

    box = locator.bounding_box()
    if box is None:
        raise AssertionError("Expected a visible element with a concrete bounding box.")
    return box


def _assert_close(name: str, left: float, right: float, *, tolerance: float = 1.5) -> None:
    """Assert two layout measurements stay within a strict visual tolerance."""

    if abs(left - right) > tolerance:
        raise AssertionError(f"{name} drifted: {left:.2f}px vs {right:.2f}px.")


def main() -> None:
    """Run the live grouping-card alignment proof and write screenshots."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    roster_name = f"PR0157 Gruppkort {int(time.time())}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1512, "height": 982})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        open_class_workspace(page, roster_name=roster_name)
        focus_workspace_mode(page, label="Grupper")

        new_draft_button = page.locator('[data-test="new-grouping-draft"]')
        expect(new_draft_button).to_be_visible()
        new_draft_button.click()

        first_card = page.locator('[data-test="group-card"]').first
        expect(first_card).to_be_visible()
        expect(page.get_by_text("Gruppnamn", exact=True)).to_have_count(0)

        name_input = first_card.locator('[data-test="group-name-input"]')
        move_up_button = first_card.locator('[data-test="move-group-up"]')
        move_down_button = first_card.locator('[data-test="move-group-down"]')
        remove_button = first_card.locator('[data-test="remove-group"]')

        input_box = _bounding_box(name_input)
        move_up_box = _bounding_box(move_up_button)
        move_down_box = _bounding_box(move_down_button)
        remove_box = _bounding_box(remove_button)

        _assert_close("group name/button top edge", input_box["y"], move_up_box["y"])
        _assert_close("group name/button top edge", input_box["y"], move_down_box["y"])
        _assert_close("group name/button top edge", input_box["y"], remove_box["y"])
        _assert_close("group name/button height", input_box["height"], move_up_box["height"])
        _assert_close("group name/button height", input_box["height"], move_down_box["height"])
        _assert_close("group name/button height", input_box["height"], remove_box["height"])

        # Prove the three action buttons stayed on the same row beside the input.
        _assert_close("group action row alignment", move_up_box["y"], move_down_box["y"])
        _assert_close("group action row alignment", move_up_box["y"], remove_box["y"])
        if move_up_box["x"] <= input_box["x"]:
            raise AssertionError("Group action buttons did not stay beside the name field.")

        page.screenshot(path=str(ARTIFACTS_DIR / "group-card-alignment.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright grouping alignment proof screenshots written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
