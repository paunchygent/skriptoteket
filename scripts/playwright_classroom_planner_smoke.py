"""Canonical Playwright smoke for the Klassrumskartan planner app.

This script is the shipped planner's canonical browser baseline. It reuses the
repo's shared Playwright config and Chromium launch fallback, logs in through
the protected app route, creates a small real class list and classroom, walks
through the current class-first workspace flow, and verifies that the live
planner still works without relying on PR-specific shortcuts.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    close_history_drawer,
    create_roster,
    create_template,
    delete_remaining_historic_seating_draft,
    exit_to_origin,
    login_to_app,
    open_class_workspace,
    open_grouping_history,
    open_grouping_workspace,
    open_rules_workspace,
    open_seating_workspace,
    reopen_historic_seating_draft,
    return_to_class_workspace,
    start_second_seating_draft,
    switch_seating_workspace_template,
    verify_grouping_history_starts_empty,
    verify_seating_history_starts_empty,
    verify_seating_toolbar,
    verify_seating_zoom_surface,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/classroom-planner-smoke")


def _exercise_grouping_fundamentals(page: Page) -> None:
    """Verify blank grouping drafts plus browser-level undo/redo inside grouping."""

    first_group_name = page.locator("input[type='text']").first
    redo_button = page.locator('[data-test="redo-grouping"]')

    page.get_by_role("button", name=re.compile(r"Nytt (grupputkast|utkast)", re.IGNORECASE)).click()
    expect(first_group_name).to_be_enabled()
    expect(first_group_name).to_have_value("Grupp 1")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Grupp 2")
    expect(page.locator("aside").get_by_text("2", exact=True)).to_be_visible()
    expect(redo_button).to_be_disabled()

    first_group_name.fill("Arbetslag Alfa")
    first_group_name.press("Enter")
    expect(first_group_name).to_have_value("Arbetslag Alfa")

    page.locator('[data-test="undo-grouping"]').click()
    expect(first_group_name).to_have_value("Grupp 1")
    expect(redo_button).to_be_enabled()

    redo_button.click()
    expect(first_group_name).to_have_value("Arbetslag Alfa")


def _start_second_grouping_draft(page: Page) -> None:
    """Create a second blank grouping draft so the first one moves to history."""

    first_group_name = page.locator("input[type='text']").first

    page.get_by_role("button", name=re.compile(r"Nytt (grupputkast|utkast)", re.IGNORECASE)).click()
    expect(first_group_name).to_have_value("Grupp 1")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Grupp 2")


def _reopen_historic_grouping_draft(page: Page) -> None:
    """Open the older grouping draft from the history drawer overlay."""

    open_grouping_history(page)
    expect(page.get_by_text("Aktuellt grupputkast", exact=True)).to_be_visible()
    history_button = page.get_by_role(
        "button", name=re.compile(r"Revision \d+", re.IGNORECASE)
    ).first
    history_button.click()
    expect(page.locator("input[type='text']").first).to_have_value("Arbetslag Alfa")
    open_grouping_history(page)
    expect(page.get_by_text("Aktivt nu", exact=True)).to_be_visible()
    close_history_drawer(page, title="Grupper")


def _delete_remaining_historic_grouping_draft(page: Page) -> None:
    """Delete one historic grouping draft and keep the active draft intact."""

    open_grouping_history(page)
    initial_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    page.get_by_role("button", name="Ta bort historiskt utkast").first.click()
    confirmation = page.locator("article").filter(
        has=page.get_by_text("Ta bort utkast?", exact=True)
    )
    expect(confirmation).to_be_visible()
    confirmation.get_by_role(
        "button",
        name=re.compile(r"^Ta bort$", re.IGNORECASE),
    ).click(force=True)
    page.wait_for_timeout(500)
    open_grouping_history(page)
    remaining_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    assert remaining_history_count == initial_history_count - 1
    if remaining_history_count == 0:
        expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    close_history_drawer(page, title="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()


def main() -> None:
    """Run the reusable Klassrumskartan browser smoke."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW Klass {run_suffix}"
    first_template_name = f"PW Sal A {run_suffix}"
    second_template_name = f"PW Sal B {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=first_template_name)
        create_template(page, template_name=second_template_name)
        open_class_workspace(page, roster_name=roster_name)
        open_grouping_workspace(page, template_name=first_template_name)
        verify_grouping_history_starts_empty(page)
        _exercise_grouping_fundamentals(page)
        _start_second_grouping_draft(page)
        _reopen_historic_grouping_draft(page)
        _delete_remaining_historic_grouping_draft(page)
        expect(page.locator("input[type='text']").first).to_have_value("Arbetslag Alfa")
        open_seating_workspace(page, template_name=first_template_name)
        switch_seating_workspace_template(page, template_name=second_template_name)
        verify_seating_toolbar(page)
        verify_seating_zoom_surface(page)
        verify_seating_history_starts_empty(page)
        start_second_seating_draft(page)
        reopen_historic_seating_draft(page)
        delete_remaining_historic_seating_draft(page)
        open_rules_workspace(page)
        return_to_class_workspace(page)
        exit_to_origin(page)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "classroom-planner-smoke.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
