"""Playwright proof for PR-0315 phone active-rule management.

Purpose:
    Exercise the public Klassrumskartan guest route at an iPhone 15 Pro
    viewport and prove that phone `Regler` exposes persisted-rule management
    for all rule families without inventing a phone-only persistence model.

Relationships:
    - Proves both authenticated and public guest state so the shared UI-state
      behavior cannot drift between planner session owners.
    - Reuses shared workspace-mode helpers from the Klassrumskartan Playwright
      support module.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Callable, Sequence

from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0315-phone-rules-active-management")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
AUTH_APP_PATH = "/apps/classroom.group-seating-studio"


def _first_visible(page: Page, selector: str) -> Locator:
    """Return the first visible element for a selector list."""

    locator = page.locator(selector)
    for _ in range(60):
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
        page.wait_for_timeout(100)
    raise AssertionError(f"No visible element matched {selector!r}.")


def _wait_for_select_option(page: Page, *, selector: str, label: str) -> str:
    """Wait for a select option containing a label and return its value."""

    selects = page.locator(selector)
    for _ in range(60):
        for index in range(selects.count()):
            select = selects.nth(index)
            if not select.is_visible():
                continue
            options = select.evaluate(
                """element => Array.from(element.options).map(option => ({
                    value: option.value,
                    label: option.label,
                }))"""
            )
            for option in options:
                if option["value"] and label in option["label"]:
                    return str(option["value"])
        page.wait_for_timeout(150)
    raise AssertionError(f"{label!r} did not appear in {selector!r}.")


def _assert_touch_targets(locator: Locator, *, label: str) -> None:
    """Assert that all visible matched buttons expose safe phone touch targets."""

    boxes = [
        box
        for box in locator.evaluate_all(
            """elements => elements
                .filter(element => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
                })
                .map(element => {
                    const rect = element.getBoundingClientRect();
                    return { width: rect.width, height: rect.height };
                })"""
        )
        if box is not None
    ]
    if not boxes:
        raise AssertionError(f"{label} did not expose visible targets.")
    undersized = [
        f"{box['width']}x{box['height']}"
        for box in boxes
        if box["width"] < 44 or box["height"] < 44
    ]
    if undersized:
        raise AssertionError(f"{label} touch target(s) too small: {', '.join(undersized)}.")


def _create_roster(page: Page, *, roster_name: str) -> None:
    """Create one public roster through the overview UI."""

    _first_visible(
        page, '[data-test="overview-create-roster"], [data-test="phone-overview-create-roster"]'
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg\nCecilia Ceder\nDavid Dahl")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    _wait_for_select_option(
        page,
        selector='[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]',
        label=roster_name,
    )


def _create_template(page: Page, *, template_name: str) -> None:
    """Create one public classroom with two selectable seats."""

    _first_visible(
        page, '[data-test="overview-create-template"], [data-test="phone-overview-create-template"]'
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    expect(grid_buttons.nth(0)).to_be_visible()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    page.locator('[data-test="room-template-save-button"]').click()
    _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )


def _select_assets(page: Page, *, roster_name: str, template_name: str) -> None:
    """Select the active public roster and classroom."""

    roster_value = _wait_for_select_option(
        page,
        selector='[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]',
        label=roster_name,
    )
    template_value = _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )
    _first_visible(
        page, '[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]'
    ).select_option(value=roster_value)
    _first_visible(
        page, '[data-test="overview-template-select"], [data-test="phone-overview-template-select"]'
    ).select_option(value=template_value)


def _select_student_from_phone_pool(page: Page, student_name: str) -> None:
    """Select one student through the phone rule student pool."""

    page.locator('[data-test="phone-rules-student-pool"]').get_by_role(
        "button", name=re.compile(re.escape(student_name))
    ).click()


def _select_student_from_desktop_rules_map(page: Page, student_name: str) -> None:
    """Select one student through the desktop rules map roster tray."""

    page.locator('[data-test="rules-map-unplaced"]').get_by_role(
        "button", name=re.compile(re.escape(student_name))
    ).click()


def _open_overview(page: Page) -> None:
    """Return to the phone overview workspace."""

    focus_workspace_mode(page, label="Översikt")
    _first_visible(
        page, '[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]'
    )


def _create_fixed_seat_rule(page: Page) -> None:
    """Create one active-template fixed-seat rule through the phone workflow."""

    page.locator('[data-test="phone-rules-tool-fixed_seat"]').click()
    expect(page.locator('[data-test="phone-fixed-seat-map"]')).to_be_visible()
    _select_student_from_phone_pool(page, "Ada Lovelace")
    page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]').click()
    expect(page.locator('[data-test="phone-rules-commit-fixed-seat"]')).to_be_enabled()
    page.locator('[data-test="phone-rules-commit-fixed-seat"]').click()
    expect(page.locator('[data-test="phone-rules-active-row-fixed-seat"]')).to_be_visible()


def _create_near_teacher_rule(page: Page) -> None:
    """Create one consolidated near-teacher rule through the phone workflow."""

    page.locator('[data-test="phone-rules-tool-near_teacher"]').click()
    _select_student_from_phone_pool(page, "Bo Berg")
    _select_student_from_phone_pool(page, "Cecilia Ceder")
    expect(page.locator('[data-test="phone-rules-commit-rule"]')).to_be_enabled()
    page.locator('[data-test="phone-rules-commit-rule"]').click()
    expect(page.locator('[data-test="phone-rules-active-row-near-teacher"]')).to_be_visible()


def _create_relationship_rule(page: Page) -> None:
    """Create one relationship rule through the phone workflow."""

    page.locator('[data-test="phone-rules-tool-keep_near"]').click()
    _select_student_from_phone_pool(page, "Cecilia Ceder")
    _select_student_from_phone_pool(page, "David Dahl")
    expect(page.locator('[data-test="phone-rules-commit-rule"]')).to_be_enabled()
    page.locator('[data-test="phone-rules-commit-rule"]').click()
    expect(page.locator('[data-test="phone-rules-active-row-relationship"]')).to_be_visible()


def _assert_summary_count(page: Page, expected: int) -> None:
    """Assert the active-rule summary count."""

    expect(page.locator('[data-test="phone-rules-active-count"]')).to_have_text(str(expected))


def _wait_for_saved_status(page: Page) -> None:
    """Wait until authenticated smart-rule autosave has settled."""

    status = page.locator('[data-test="planner-top-panel-status-label"]')
    for _ in range(80):
        if status.count() > 0 and status.first.is_visible():
            if "sparad" in status.first.inner_text().strip().lower():
                return
        page.wait_for_timeout(250)
    raise AssertionError("Planner status did not reach Sparad before reload.")


def _assert_phone_entry_has_no_transient_rule_candidates(page: Page) -> None:
    """Assert persisted rules do not reopen as phone candidate selections."""

    expect(page.locator('[data-test="phone-rules-active-row-near-teacher"]')).to_be_visible()
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(0)
    expect(page.locator('[data-test="phone-rules-commit-rule"]')).to_be_disabled()


def _assert_candidate_clear_remains_cleared(page: Page) -> None:
    """Assert cleared edit candidates do not repopulate from persisted rule state."""

    page.locator('[data-test="phone-rules-edit-rule-0"]').click()
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(2)

    page.locator('[data-test="phone-rules-clear-selection"]').click()
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(0)
    expect(page.locator('[data-test="phone-rules-commit-rule"]')).to_be_disabled()
    page.wait_for_timeout(1_200)
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(0)

    _select_student_from_phone_pool(page, "Ada Lovelace")
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(1)
    page.locator('[data-test="phone-rules-selected-student"]').get_by_role(
        "button", name=re.compile(r"Ta bort Ada Lovelace")
    ).click()
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(0)
    page.wait_for_timeout(1_200)
    expect(page.locator('[data-test="phone-rules-selected-student"]')).to_have_count(0)


def _assert_desktop_candidate_clear_remains_cleared(page: Page) -> None:
    """Assert hydrated desktop edit candidates can be cleared and removed."""

    page.locator('[data-test="rules-edit-rule-0"]').click()
    pending_chips = page.locator(
        '[data-test="rules-tool-rail"] [data-test="rules-pending-student-chip"]'
    )
    expect(pending_chips).to_have_count(2)

    page.locator('[data-test="rules-tool-rail"]').get_by_role(
        "button", name=re.compile(r"Rensa markering", re.IGNORECASE)
    ).click()
    expect(pending_chips).to_have_count(0)
    expect(
        page.locator('[data-test="rules-tool-rail"]').get_by_role(
            "button", name=re.compile(r"Spara regel", re.IGNORECASE)
        )
    ).to_be_disabled()
    page.wait_for_timeout(1_200)
    expect(pending_chips).to_have_count(0)

    _select_student_from_desktop_rules_map(page, "Ada Lovelace")
    expect(pending_chips).to_have_count(1)
    _select_student_from_desktop_rules_map(page, "Ada Lovelace")
    expect(pending_chips).to_have_count(0)
    page.wait_for_timeout(1_200)
    expect(pending_chips).to_have_count(0)


def _assert_desktop_entry_has_no_transient_rule_candidates(page: Page) -> None:
    """Assert persisted rules do not reopen as desktop candidate chips."""

    near_teacher_card = page.locator('[data-test="rules-active-card"]').filter(
        has_text="Nära läraren"
    )
    expect(near_teacher_card).to_have_count(1)
    expect(
        page.locator('[data-test="rules-tool-rail"] [data-test="rules-pending-student-chip"]')
    ).to_have_count(0)


def _reload_rules_workspace(
    page: Page,
    *,
    roster_name: str,
    template_name: str,
) -> None:
    """Reload the app, restore class context, and return to hydrated phone rules."""

    page.reload(wait_until="domcontentloaded")
    wait_for_app_heading(page)
    focus_workspace_mode(page, label="Översikt")
    _select_assets(page, roster_name=roster_name, template_name=template_name)
    focus_workspace_mode(page, label="Regler")
    _first_visible(
        page,
        '[data-test="phone-rules-active-summary"], [data-test="rules-summary-panel"]',
    )


def _run_surface(
    *,
    base_url: str,
    path: str,
    surface: str,
    enter_surface: Callable[[Page], None],
) -> None:
    """Run the phone active-rule management proof against one planner surface."""

    run_suffix = str(int(time.time()))
    roster_name = f"PR0315 {surface} Klass {run_suffix}"
    template_name = f"PR0315 {surface} Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()
        enter_surface(page)
        try:
            wait_for_app_heading(page)
        except AssertionError:
            failure_path = ARTIFACTS_DIR / f"{surface}-render-failed.png"
            page.screenshot(path=str(failure_path), full_page=True)
            body_text = page.locator("body").inner_text(timeout=2_000)
            raise AssertionError(
                f"Klassrumskartan did not render on {surface}. "
                f"url={page.url} screenshot={failure_path} body={body_text[:500]!r}"
            ) from None
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _select_assets(page, roster_name=roster_name, template_name=template_name)

        focus_workspace_mode(page, label="Regler")
        expect(page.locator('[data-test="phone-rules-active-summary"]')).to_have_count(0)
        _create_fixed_seat_rule(page)
        _wait_for_saved_status(page)
        _assert_summary_count(page, 1)

        _create_near_teacher_rule(page)
        _wait_for_saved_status(page)
        _create_relationship_rule(page)
        _wait_for_saved_status(page)
        _reload_rules_workspace(page, roster_name=roster_name, template_name=template_name)
        _assert_phone_entry_has_no_transient_rule_candidates(page)
        _assert_candidate_clear_remains_cleared(page)
        _assert_summary_count(page, 3)
        _assert_touch_targets(
            page.locator(".planner-phone-rule-action-button"),
            label="phone active-rule edit/delete buttons",
        )

        page.locator('[data-test="phone-rules-active-summary-toggle"]').click()
        expect(page.locator('[data-test="phone-rules-active-list"]')).to_have_count(0)
        page.locator('[data-test="phone-rules-active-summary-toggle"]').click()
        expect(page.locator('[data-test="phone-rules-active-list"]')).to_be_visible()

        page.screenshot(path=str(ARTIFACTS_DIR / f"{surface}-phone-active-rules-all-families.png"))

        page.locator('[data-test="phone-rules-delete-rule-0"]').click()
        expect(page.locator('[data-test="phone-rules-active-row-relationship"]')).to_have_count(0)
        _assert_summary_count(page, 2)

        page.locator('[data-test="phone-rules-delete-near-teacher"]').click()
        expect(page.locator('[data-test="phone-rules-active-row-near-teacher"]')).to_have_count(0)
        _assert_summary_count(page, 1)

        page.locator('[data-test^="phone-rules-delete-fixed-seat-"]').click()
        expect(page.locator('[data-test="phone-rules-active-summary"]')).to_have_count(0)
        page.screenshot(path=str(ARTIFACTS_DIR / f"{surface}-phone-active-rules-empty-hidden.png"))

        context.close()
        browser.close()

    print(f"pr-0315-phone-rules-active-management:{surface}: ok")


def _run_public(*, base_url: str) -> None:
    """Run the public guest phone proof."""

    def enter_public(page: Page) -> None:
        page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")

    _run_surface(
        base_url=base_url,
        path=PUBLIC_APP_PATH,
        surface="public",
        enter_surface=enter_public,
    )


def _run_auth_session(*, base_url: str, email: str, password: str) -> None:
    """Run the authenticated phone proof through the canonical auth entry."""

    def enter_auth(page: Page) -> None:
        login_to_app(
            page,
            base_url=base_url.rstrip("/"),
            email=email,
            password=password,
        )

    _run_surface(
        base_url=base_url,
        path=AUTH_APP_PATH,
        surface="auth",
        enter_surface=enter_auth,
    )


def _run_auth_desktop_session(*, base_url: str, email: str, password: str) -> None:
    """Run the authenticated desktop rehydration proof for shared rule edit state."""

    run_suffix = str(int(time.time()))
    roster_name = f"PR0315 desktop Klass {run_suffix}"
    template_name = f"PR0315 desktop Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        login_to_app(
            page,
            base_url=base_url.rstrip("/"),
            email=email,
            password=password,
        )
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _select_assets(page, roster_name=roster_name, template_name=template_name)

        focus_workspace_mode(page, label="Regler")
        page.locator('[data-test="rules-tool-near_teacher"]').click()
        _select_student_from_desktop_rules_map(page, "Ada Lovelace")
        _select_student_from_desktop_rules_map(page, "Bo Berg")
        expect(
            page.locator('[data-test="rules-tool-rail"] [data-test="rules-pending-student-chip"]')
        ).to_have_count(2)
        page.locator('[data-test="rules-tool-rail"]').get_by_role(
            "button", name=re.compile(r"Skapa regel", re.IGNORECASE)
        ).click()
        expect(
            page.locator('[data-test="rules-active-card"]').filter(has_text="Nära läraren")
        ).to_have_count(1)
        _wait_for_saved_status(page)

        page.locator('[data-test="rules-tool-keep_near"]').click()
        _select_student_from_desktop_rules_map(page, "Cecilia Ceder")
        _select_student_from_desktop_rules_map(page, "David Dahl")
        expect(
            page.locator('[data-test="rules-tool-rail"] [data-test="rules-pending-student-chip"]')
        ).to_have_count(2)
        page.locator('[data-test="rules-tool-rail"]').get_by_role(
            "button", name=re.compile(r"Skapa regel", re.IGNORECASE)
        ).click()
        expect(page.locator('[data-test="rules-active-card"]')).to_have_count(2)
        _wait_for_saved_status(page)

        _reload_rules_workspace(page, roster_name=roster_name, template_name=template_name)
        _assert_desktop_entry_has_no_transient_rule_candidates(page)
        _assert_desktop_candidate_clear_remains_cleared(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "auth-desktop-rules-edit-clear-rehydrated.png"))

        context.close()
        browser.close()

    print("pr-0315-phone-rules-active-management:auth-desktop: ok")


def _run(*, base_url: str, email: str, password: str) -> None:
    """Run the PR-0315 phone active-rule management proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    _run_auth_session(base_url=base_url, email=email, password=password)
    _run_auth_desktop_session(base_url=base_url, email=email, password=password)
    _run_public(base_url=base_url)
    print(f"pr-0315-phone-rules-active-management: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the PR-0315 browser proof."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--start-vite", action="store_true")
    proof_args, config_argv = parser.parse_known_args(argv)
    config = get_config(config_argv)
    _ = proof_args
    _run(base_url=config.base_url, email=config.email, password=config.password)


if __name__ == "__main__":  # pragma: no cover
    main()
