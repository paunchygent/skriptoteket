"""Focused Playwright proof for PR-0136 room-editor toggle removal polish.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This browser check validates the live classroom editor behavior newly extended
in PR-0136: floor fixtures and wall fixtures should toggle off when clicked
again with the same tool selected, while conflicting different-tool clicks must
leave the existing object intact.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0136-room-editor-toggle-check")


def _select_overview_template(page: Page, *, template_name: str) -> None:
    """Select one room template in the overview panel by visible label."""

    overview_select = page.locator('[data-test="overview-template-select"]')
    expect(overview_select).to_be_visible()
    option_rows = overview_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and template_name in option["label"]
    )
    overview_select.select_option(value=matching_option["value"])
    expect(overview_select).to_have_value(matching_option["value"])


def _open_template_edit_modal(page: Page) -> None:
    """Open the edit modal from the overview template panel."""

    page.get_by_role("button", name=re.compile(r"Redigera klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).to_be_visible()


def _edit_modal(page: Page) -> Locator:
    """Return the active room-template modal container."""

    return page.locator("div.fixed.inset-0.z-50").last


def _grid_buttons(page: Page) -> Locator:
    """Return the interactive builder cell locator inside the edit modal."""

    return _edit_modal(page).locator("section .relative.grid.gap-1 button[type='button']")


def _clear_builder_hover(page: Page) -> None:
    """Move the pointer away from the builder so ghost overlays disappear."""

    _edit_modal(page).get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).hover()


def _assert_floor_fixture_toggle_and_conflict(page: Page) -> None:
    """Verify same-tool fixture removal and different-tool conflict preservation."""

    modal = _edit_modal(page)
    builder_viewport = modal.locator('[data-test="room-builder-viewport"]')
    target_cell = _grid_buttons(page).nth(15)

    modal.get_by_role("button", name=re.compile(r"Kateder", re.IGNORECASE)).click()
    target_cell.click()
    _clear_builder_hover(page)
    teacher_desk_label = builder_viewport.get_by_text(re.compile(r"Kateder", re.IGNORECASE))
    expect(teacher_desk_label.first).to_be_visible()

    target_cell.click()
    _clear_builder_hover(page)
    expect(teacher_desk_label).to_have_count(0)

    modal.get_by_role("button", name=re.compile(r"Kateder", re.IGNORECASE)).click()
    target_cell.click()
    _clear_builder_hover(page)
    expect(teacher_desk_label.first).to_be_visible()

    modal.get_by_role("button", name=re.compile(r"Runt bord", re.IGNORECASE)).click()
    target_cell.click()
    _clear_builder_hover(page)

    expect(teacher_desk_label.first).to_be_visible()
    expect(
        modal.get_by_text(re.compile(r"krockar med befintlig möblering", re.IGNORECASE))
    ).to_be_visible()


def _assert_wall_fixture_toggle(page: Page) -> None:
    """Verify same-tool clicks toggle an existing wall object off."""

    modal = _edit_modal(page)
    builder_viewport = modal.locator('[data-test="room-builder-viewport"]')
    whiteboard_cell = _grid_buttons(page).nth(2)

    modal.get_by_role("button", name=re.compile(r"Whiteboard", re.IGNORECASE)).click()
    whiteboard_cell.click(position={"x": 48, "y": 4})
    _clear_builder_hover(page)
    whiteboard_label = builder_viewport.get_by_text(re.compile(r"Whiteboard", re.IGNORECASE))
    expect(whiteboard_label.first).to_be_visible()

    whiteboard_cell.click(position={"x": 48, "y": 4})
    _clear_builder_hover(page)
    expect(whiteboard_label).to_have_count(0)


def main() -> None:
    """Run the focused PR-0136 room-editor toggle-removal validation."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0136 Klass {run_suffix}"
    template_name = f"PW PR0136 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        page.goto(f"{base_url}/apps/classroom.group-seating-studio", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        open_class_workspace(page, roster_name=roster_name)
        focus_workspace_mode(page, label="Översikt")
        _select_overview_template(page, template_name=template_name)
        _open_template_edit_modal(page)

        _assert_floor_fixture_toggle_and_conflict(page)
        _assert_wall_fixture_toggle(page)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "room-editor-toggle-check.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"playwright-pr-0136: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
