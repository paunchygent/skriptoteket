"""Focused Playwright proof for seating editor sync and overflow parity.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This check reproduces the live seating-workspace classroom-edit flow, verifies
that saved classroom changes immediately update the active seating canvas
without leaving the workspace, and confirms the seating overflow now exposes
both class and classroom editing while grouping keeps only class editing.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0165-seating-editor-sync-check")


def _select_template_in_workspace(page: Page, *, test_id: str, template_name: str) -> None:
    """Select a room template by label inside one planner workspace control."""

    template_select = page.locator(f'[data-test="{test_id}"]')
    expect(template_select).to_be_visible()
    option_rows = template_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and template_name in option["label"]
    )
    template_select.select_option(value=matching_option["value"])
    expect(template_select).to_have_value(matching_option["value"])


def _open_seating_workspace(page: Page, *, template_name: str) -> None:
    """Open seating from the shared mode toggle and bind it to one classroom."""

    focus_workspace_mode(page, label="Sittplatser")
    _select_template_in_workspace(
        page,
        test_id="seating-template-select",
        template_name=template_name,
    )
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _open_grouping_workspace(page: Page, *, template_name: str) -> None:
    """Open grouping and keep the same classroom as optional context."""

    focus_workspace_mode(page, label="Grupper")
    _select_template_in_workspace(
        page,
        test_id="grouping-template-select",
        template_name=template_name,
    )
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()


def _verify_seating_overflow_actions(page: Page) -> None:
    """Confirm seating exposes both class and classroom edit actions."""

    page.locator('[data-test="seating-actions-menu"]').click()
    edit_class = page.locator('[data-test="edit-seating-roster"]')
    edit_classroom = page.locator('[data-test="edit-current-template"]')
    expect(edit_class).to_be_visible()
    expect(edit_class).to_have_text(re.compile(r"Redigera klass", re.IGNORECASE))
    expect(edit_classroom).to_be_visible()
    expect(edit_classroom).to_have_text(re.compile(r"Redigera klassrum", re.IGNORECASE))

    edit_class.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Avbryt", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).not_to_be_visible()

    page.locator('[data-test="seating-actions-menu"]').click()
    page.locator('[data-test="edit-current-template"]').click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).to_be_visible()


def _add_two_seats_and_save(page: Page) -> None:
    """Add two seats in the live classroom editor, then save the room."""

    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    grid_buttons.nth(2).click()
    grid_buttons.nth(3).click()
    page.get_by_role("button", name=re.compile(r"Spara klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).not_to_be_visible()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _verify_seating_workspace_refresh(page: Page) -> None:
    """Confirm the saved classroom updates the live seating workspace immediately."""

    template_select = page.locator('[data-test="seating-template-select"]')
    selected_label = template_select.evaluate(
        'element => element.options[element.selectedIndex]?.label ?? ""'
    )
    assert "4 platser" in selected_label
    expect(page.locator('[data-test="room-seat-token"]')).to_have_count(4)


def _verify_grouping_overflow_scope(page: Page) -> None:
    """Confirm grouping keeps class editing but not classroom editing."""

    page.locator('[data-test="grouping-actions-menu"]').click()
    expect(page.locator('[data-test="edit-grouping-roster"]')).to_be_visible()
    expect(page.locator('[data-test="edit-current-template"]')).to_have_count(0)


def main() -> None:
    """Run the focused seating editor sync validation."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0165 Klass {run_suffix}"
    template_name = f"PW PR0165 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        open_class_workspace(page, roster_name=roster_name)

        _open_seating_workspace(page, template_name=template_name)
        _verify_seating_overflow_actions(page)
        _add_two_seats_and_save(page)
        _verify_seating_workspace_refresh(page)
        page.screenshot(
            path=str(ARTIFACTS_DIR / "seating-editor-sync.png"),
            full_page=True,
        )

        _open_grouping_workspace(page, template_name=template_name)
        _verify_grouping_overflow_scope(page)
        page.screenshot(
            path=str(ARTIFACTS_DIR / "grouping-overflow-scope.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
