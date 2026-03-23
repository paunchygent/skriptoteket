"""Dedicated live browser proof for PR-0112 workspace simplification.

This script reuses the established Klassrumskartan Playwright helpers to log in
through the protected curated-app route, open a known live class workspace, and
verify the PR-0112 transition/layout contracts against the canonical local dev
runtime. It focuses on the accepted review fixes and design goals rather than
retesting the broader grouping/seating lifecycle that already has dedicated
proofs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_classroom_planner_smoke import _login_to_app, _open_class_workspace
from scripts.playwright_ui_smoke import _launch_chromium

APP_PATH = "/apps/classroom.group-seating-studio"
ARTIFACTS_DIR = Path(".artifacts/pr-0112-live-check")
ROSTER_NAME = "DBG CTA 1774193634"
PREFERRED_TEMPLATE_NAME = "G20"


def _dismiss_resumable_cta(page: Any) -> None:
    """Close the landing CTA so the canonical class cards are reachable."""

    dismiss_button = page.get_by_role("button", name="Stäng")
    if dismiss_button.count() > 0 and dismiss_button.first.is_visible():
        dismiss_button.first.click()


def _expect_overview_mode(page: Any) -> None:
    """Assert the class workspace starts in overview mode."""

    overview_button = page.get_by_role("button", name="Översikt", exact=True)
    grouping_button = page.get_by_role("button", name="Grupper", exact=True)
    seating_button = page.get_by_role("button", name="Sittplatser", exact=True)
    expect(page.get_by_text("Klassarbetsyta", exact=True)).to_be_visible()
    expect(overview_button).to_have_attribute("aria-pressed", "true")
    expect(grouping_button).to_have_attribute("aria-pressed", "false")
    expect(seating_button).to_have_attribute("aria-pressed", "false")


def _expect_grouping_mode(page: Any) -> None:
    """Assert grouping opens with the simplified toolbar and no duplicated edit action."""

    grouping_button = page.get_by_role("button", name="Grupper", exact=True)
    seating_button = page.get_by_role("button", name="Sittplatser", exact=True)
    expect(grouping_button).to_have_attribute("aria-pressed", "true")
    expect(seating_button).to_have_attribute("aria-pressed", "false")
    expect(page.locator('[data-test="grouping-template-select"]')).to_be_visible()
    expect(page.locator('[data-test="randomize-groups"]')).to_be_visible()
    expect(page.locator('[data-test="grouping-history"]')).to_have_count(0)
    expect(page.locator('[data-test="edit-grouping-roster"]')).to_have_count(0)
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()


def _select_available_grouping_template(page: Any) -> str:
    """Choose a real grouping classroom option, preferring the configured room name."""

    page.get_by_role("button", name="Grupper", exact=True).click()
    template_select = page.locator('[data-test="grouping-template-select"]')
    expect(template_select).to_be_visible()
    option_rows = template_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        (
            option
            for option in option_rows
            if option["value"] and PREFERRED_TEMPLATE_NAME in option["label"]
        ),
        None,
    )
    if matching_option is None:
        matching_option = next(option for option in option_rows if option["value"])
    template_select.select_option(value=matching_option["value"])
    expect(template_select).to_have_value(matching_option["value"])
    return str(matching_option["value"])


def _expect_grouping_overflow_items(page: Any) -> None:
    """Open the grouping overflow and assert the low-priority actions live there."""

    page.locator('[data-test="grouping-actions-menu"]').click()
    history_item = page.locator('[data-test="grouping-history"]')
    edit_item = page.locator('[data-test="edit-grouping-roster"]')
    expect(history_item).to_be_visible()
    expect(edit_item).to_be_visible()
    expect(history_item).to_have_text(re.compile(r"Historik", re.IGNORECASE))
    expect(edit_item).to_have_text(re.compile(r"Redigera klass", re.IGNORECASE))
    page.keyboard.press("Escape")


def _expect_seating_mode(page: Any) -> None:
    """Assert seating keeps critical actions visible and low-priority actions collapsed."""

    grouping_button = page.get_by_role("button", name="Grupper", exact=True)
    seating_button = page.get_by_role("button", name="Sittplatser", exact=True)
    expect(grouping_button).to_have_attribute("aria-pressed", "false")
    expect(seating_button).to_have_attribute("aria-pressed", "true")
    expect(page.locator('[data-test="seating-template-select"]')).to_be_visible()
    expect(page.locator('[data-test="randomize-seating"]')).to_be_visible()
    expect(page.locator('[data-test="new-seating-draft"]')).to_be_visible()
    expect(page.locator('[data-test="seating-history"]')).to_have_count(0)
    expect(page.locator('[data-test="edit-current-template"]')).to_have_count(0)
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _expect_seating_overflow_items(page: Any) -> None:
    """Open the seating overflow and assert secondary actions stay available there."""

    page.locator('[data-test="seating-actions-menu"]').click()
    history_item = page.locator('[data-test="seating-history"]')
    edit_item = page.locator('[data-test="edit-current-template"]')
    expect(history_item).to_be_visible()
    expect(edit_item).to_be_visible()
    expect(history_item).to_have_text(re.compile(r"Historik", re.IGNORECASE))
    expect(edit_item).to_have_text(re.compile(r"Redigera klassrum", re.IGNORECASE))
    page.keyboard.press("Escape")


def main() -> None:
    """Run the focused PR-0112 workspace transition proof against local dev."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        _login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        _dismiss_resumable_cta(page)
        _open_class_workspace(page, roster_name=ROSTER_NAME)
        _expect_overview_mode(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "overview.png"), full_page=True)

        selected_template_id = _select_available_grouping_template(page)
        _expect_grouping_mode(page)
        _expect_grouping_overflow_items(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "groups.png"), full_page=True)

        page.get_by_role("button", name="Sittplatser", exact=True).click()
        expect(page.locator('[data-test="seating-template-select"]')).to_be_visible()
        expect(page.locator('[data-test="seating-template-select"]')).to_have_value(
            selected_template_id
        )
        _expect_seating_mode(page)
        _expect_seating_overflow_items(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "seating.png"), full_page=True)

        context.close()
        browser.close()

    print(f"playwright-pr0112: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
