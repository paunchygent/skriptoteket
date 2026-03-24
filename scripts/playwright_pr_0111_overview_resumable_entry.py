"""Dedicated live browser proof for PR-0111 overview resumable entry polish.

This script reuses the established classroom-planner Playwright helpers to log
in through the protected curated-app route, create one real class list and
classroom, seed active grouping and seating drafts through the live UI, and
then verify the compact overview-owned continuation surface. The proof focuses
on the accepted PR-0111 behavior: separate grouping/seating continue cards,
compact settings affordances, dismiss `×`, and direct entry into the correct
workspace without relying on the old landing CTA.
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
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0111-live-check")
APP_PATH = "/apps/classroom.group-seating-studio"


def _dismiss_landing_resumable_cta(page: Any) -> None:
    """Close the legacy landing CTA if it is present before class selection."""

    dismiss_button = page.get_by_role("button", name=re.compile(r"Stäng senaste utkastet"))
    if dismiss_button.count() > 0 and dismiss_button.first.is_visible():
        dismiss_button.first.click()


def _select_workspace_template(page: Any, *, template_name: str) -> None:
    """Select one classroom in overview so seating can open with room context."""

    template_select = page.locator('[data-test="overview-template-select"]')
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


def _return_to_overview(page: Any) -> None:
    """Return from one live planner workspace to the overview/main page."""

    _focus_workspace_mode(page, label="Översikt")
    expect(page.locator('[data-test="overview-roster-select"]')).to_be_visible()


def _open_grouping_draft(page: Any) -> None:
    """Open grouping once so the active grouping draft exists in the summary."""

    _focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-template-select"]')).to_be_visible()


def _open_seating_draft(page: Any, *, template_name: str) -> None:
    """Open seating once so the active seating draft exists in the summary."""

    _focus_workspace_mode(page, label="Sittplatser")
    seating_workspace = page.locator('[data-test="seating-workspace"]')
    if seating_workspace.count() > 0 and seating_workspace.first.is_visible():
        expect(seating_workspace).to_be_visible()
        return

    template_select = page.locator('[data-test="seating-template-select"]')
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
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _verify_resume_cards(page: Any, *, template_name: str) -> None:
    """Assert the compact grouping and seating continue cards render together."""

    surface = page.locator('[data-test="overview-resumable-surface"]')
    expect(surface).to_be_visible()
    expect(page.locator('[data-test="overview-grouping-resume-card"]')).to_be_visible()
    expect(page.locator('[data-test="overview-seating-resume-card"]')).to_be_visible()
    expect(surface).to_contain_text("Fortsätt grupper")
    expect(surface).to_contain_text("Fortsätt sittschema")
    expect(surface).to_contain_text(template_name)


def _close_visible_modal(page: Any, *, heading_pattern: re.Pattern[str]) -> None:
    """Close one visible planner modal through its visible header close button."""

    dialog = page.locator("div.fixed.inset-0.z-50").filter(
        has=page.get_by_role("heading", name=heading_pattern)
    )
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="×").click()


def _verify_settings_affordances(page: Any) -> None:
    """Open both settings affordances and prove they reach the expected edit modals."""

    page.locator('[data-test="grouping-draft-settings"]').click()
    roster_heading = re.compile(r"Redigera klasslista", re.IGNORECASE)
    expect(page.get_by_role("heading", name=roster_heading)).to_be_visible()
    _close_visible_modal(page, heading_pattern=roster_heading)
    expect(page.get_by_role("heading", name=roster_heading)).to_have_count(0)

    page.locator('[data-test="seating-draft-settings"]').click()
    room_heading = re.compile(r"Redigera klassrum", re.IGNORECASE)
    expect(page.get_by_role("heading", name=room_heading)).to_be_visible()
    _close_visible_modal(page, heading_pattern=room_heading)
    expect(page.get_by_role("heading", name=room_heading)).to_have_count(0)


def _verify_continue_actions(page: Any) -> None:
    """Continue each active draft from overview and prove it opens the right surface."""

    page.locator('[data-test="continue-grouping-draft"]').click()
    expect(page.locator('[data-test="grouping-template-select"]')).to_be_visible()
    _return_to_overview(page)

    page.locator('[data-test="continue-seating-draft"]').click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    _return_to_overview(page)


def _verify_dismiss_actions(page: Any) -> None:
    """Dismiss both cards through the compact `×` affordance."""

    page.locator('[data-test="dismiss-grouping-resume"]').click()
    expect(page.locator('[data-test="overview-grouping-resume-card"]')).to_have_count(0)
    expect(page.locator('[data-test="overview-seating-resume-card"]')).to_be_visible()

    page.locator('[data-test="dismiss-seating-resume"]').click()
    expect(page.locator('[data-test="overview-seating-resume-card"]')).to_have_count(0)
    expect(page.locator('[data-test="overview-resumable-surface"]')).to_have_count(0)


def main() -> None:
    """Run the focused PR-0111 proof against the canonical local SPA."""

    config = get_config()
    timestamp = int(time.time())
    roster_name = f"PR0111 Klass {timestamp}"
    template_name = f"PR0111 Sal {timestamp}"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = ARTIFACTS_DIR / "pr0111-overview-resumable-entry.png"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        _login_to_app(page, base_url=config.base_url, email=config.email, password=config.password)
        _dismiss_landing_resumable_cta(page)
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _open_class_workspace(page, roster_name=roster_name)
        _select_workspace_template(page, template_name=template_name)

        _open_grouping_draft(page)
        _return_to_overview(page)
        _open_seating_draft(page, template_name=template_name)
        _return_to_overview(page)

        _verify_resume_cards(page, template_name=template_name)
        _verify_settings_affordances(page)
        _verify_continue_actions(page)
        _verify_dismiss_actions(page)

        page.screenshot(path=str(screenshot_path), full_page=True)
        context.close()
        browser.close()

    print(f"playwright-pr0111: ok -> {screenshot_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
