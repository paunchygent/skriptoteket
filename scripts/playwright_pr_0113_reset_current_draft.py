"""Dedicated live browser proof for PR-0113 current-draft reset actions.

This script proves that `Börja om` clears grouping and seating placements
inside the currently active draft without creating a new draft, while the
existing draft-scoped undo flow can restore the cleared work. It deliberately
reuses the shared Klassrumskartan smoke helpers and the shipped seating
interaction helpers so the proof stays aligned with the repo's canonical local
browser automation patterns.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_classroom_planner_smoke import (
    _create_roster,
    _create_template,
    _focus_workspace_mode,
    _login_to_app,
    _open_class_workspace,
)
from scripts.playwright_pr_0105_seating_continuity import (
    _assign_student_to_seat,
    _unseated_pool,
    _wait_for_autosave,
)
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0113-live-check")


def _ungrouped_pool(page: Any) -> Any:
    """Return the live ungrouped-students pool in the grouping workspace."""

    return page.locator("aside").filter(has=page.get_by_text("Ej grupperade", exact=True)).first


def _randomize_grouping_assignments(page: Any) -> None:
    """Create live grouping assignments before testing the reset flow."""

    page.locator('[data-test="randomize-groups"]').click()
    expect(_ungrouped_pool(page).get_by_role("button")).to_have_count(0)
    expect(page.locator('[data-test="group-student-name"]')).to_have_count(2)


def _start_new_grouping_draft(page: Any) -> None:
    """Open a blank grouping draft before testing in-place reset."""

    _focus_workspace_mode(page, label="Grupper")
    page.locator('[data-test="new-grouping-draft"]').click()
    expect(page.locator('[data-test="group-card"]').first).to_be_visible()


def _open_seating_workspace_for_reset(page: Any, *, template_name: str) -> None:
    """Open seating and choose a room without assuming toolbar overflow state."""

    _focus_workspace_mode(page, label="Sittplatser")
    setup_surface = page.locator('[data-test="seating-workspace-setup"]')
    expect(setup_surface).to_be_visible()
    template_select = setup_surface.get_by_role("combobox")
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
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _reset_grouping_draft(page: Any) -> None:
    """Clear the current grouping draft in place and confirm the reset."""

    page.locator('[data-test="reset-grouping-draft"]').click()
    expect(page.get_by_text("Töm gruppindelningen?", exact=True)).to_be_visible()
    page.locator('[data-test="confirm-dialog-confirm"]').click()
    expect(_ungrouped_pool(page).get_by_role("button")).to_have_count(2)
    expect(
        page.locator('[data-test="group-student-name"]').filter(
            has=page.get_by_text("Ada Lovelace", exact=True)
        )
    ).to_have_count(0)


def _undo_grouping_reset(page: Any) -> None:
    """Undo one reset step and prove the grouping assignment returns."""

    undo_button = page.locator('[data-test="undo-grouping"]')
    expect(undo_button).to_be_enabled()
    undo_button.click()
    expect(_ungrouped_pool(page).get_by_role("button")).to_have_count(0)
    expect(page.locator('[data-test="group-student-name"]')).to_have_count(2)


def _reset_seating_draft(page: Any) -> None:
    """Clear the current seating draft in place and confirm the reset."""

    page.locator('[data-test="reset-seating-draft"]').click()
    expect(page.get_by_text("Töm sittplaceringarna?", exact=True)).to_be_visible()
    page.locator('[data-test="confirm-dialog-confirm"]').click()
    expect(_unseated_pool(page).get_by_role("button")).to_have_count(2)
    expect(
        page.locator('[data-test="room-seat-token"]').filter(
            has=page.get_by_text("Ada Lovelace", exact=True)
        )
    ).to_have_count(0)


def _undo_seating_reset(page: Any, *, student_name: str) -> None:
    """Undo one seating reset and prove the seat assignment returns."""

    undo_button = page.locator('[data-test="undo-seating-draft"]')
    expect(undo_button).to_be_enabled()
    undo_button.click()
    expect(_unseated_pool(page).get_by_role("button", name=re.compile(student_name))).to_have_count(
        0
    )
    expect(
        page.locator('[data-test="room-seat-token"]').filter(
            has=page.get_by_text(student_name, exact=True)
        )
    ).to_have_count(1)


def main() -> None:
    """Run the PR-0113 live reset proof against the local SPA."""

    config = get_config()
    timestamp = int(time.time())
    roster_name = f"PR0113 Klass {timestamp}"
    template_name = f"PR0113 Sal {timestamp}"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = ARTIFACTS_DIR / "pr0113-reset-current-draft.png"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})

        _login_to_app(
            page,
            base_url=config.base_url,
            email=config.email,
            password=config.password,
        )
        expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()

        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _open_class_workspace(page, roster_name=roster_name)

        _start_new_grouping_draft(page)
        _randomize_grouping_assignments(page)
        _wait_for_autosave(page)
        _reset_grouping_draft(page)
        _wait_for_autosave(page)
        _undo_grouping_reset(page)
        _wait_for_autosave(page)

        _open_seating_workspace_for_reset(page, template_name=template_name)
        _assign_student_to_seat(page, student_name="Ada Lovelace", seat_id="seat-1")
        _wait_for_autosave(page)
        _reset_seating_draft(page)
        _wait_for_autosave(page)
        _undo_seating_reset(page, student_name="Ada Lovelace")

        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    print(f"playwright-pr0113: ok -> {screenshot_path}")


if __name__ == "__main__":
    main()
