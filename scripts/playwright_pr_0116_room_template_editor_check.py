"""Focused Playwright proof for the PR-0116 room-template editor refactor.

This browser check reuses the planner smoke's protected-route login and class
workspace helpers, then validates the extracted room-template editor through a
live create/edit/delete flow. It exists to confirm the new builder/sidebar/
preview split preserves teacher-facing behavior in the local SPA.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

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
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0116-room-template-check")


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


def _edit_template(page: Page, *, edited_name: str) -> None:
    """Rename and resize the selected room template through the live editor."""

    _open_template_edit_modal(page)

    name_input = page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE))
    expect(name_input).to_be_visible()
    name_input.fill(edited_name)

    size_panel = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(r"Storlek", re.IGNORECASE))
    )
    plus_buttons = size_panel.get_by_role("button", name="+")
    expect(plus_buttons).to_have_count(2)
    plus_buttons.nth(0).click()
    plus_buttons.nth(1).click()

    page.get_by_role("button", name=re.compile(r"Spara klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).not_to_be_visible()
    option_labels = page.locator('[data-test="overview-template-select"]').evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert any(edited_name in label for label in option_labels)


def _delete_template_from_modal(page: Page, *, edited_name: str) -> None:
    """Delete the edited room template from the live edit modal."""

    _open_template_edit_modal(page)
    delete_button = page.get_by_role("button", name=re.compile(r"Radera klassrum", re.IGNORECASE))
    expect(delete_button).to_be_visible()
    delete_button.click()

    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).not_to_be_visible()

    overview_select = page.locator('[data-test="overview-template-select"]')
    option_labels = overview_select.evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert all(edited_name not in label for label in option_labels)
    expect(page.get_by_text(edited_name, exact=True)).not_to_be_visible()


def main() -> None:
    """Run the focused PR-0116 room-template editor validation."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0116 Klass {run_suffix}"
    template_name = f"PW PR0116 Sal {run_suffix}"
    edited_name = f"{template_name} Redigerad"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        open_class_workspace(page, roster_name=roster_name)
        focus_workspace_mode(page, label="Översikt")
        expect(page.get_by_role("button", name="Översikt")).to_be_visible()
        _select_overview_template(page, template_name=template_name)
        _edit_template(page, edited_name=edited_name)
        _select_overview_template(page, template_name=edited_name)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "room-template-edited.png"),
            full_page=True,
        )

        _delete_template_from_modal(page, edited_name=edited_name)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "room-template-deleted.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
