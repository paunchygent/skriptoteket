"""Reusable Playwright smoke for the Klassrumskartan planner app.

This script is the app-specific baseline for future classroom planner browser
checks. It reuses the repo's shared Playwright config and Chromium launch
fallback, logs in through the protected app route, creates a small real class
list and classroom, walks through the class-first workspace flow, and verifies
that the live planner can still be reached without relying on PR-specific
shortcuts.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium, _login

APP_PATH = "/apps/classroom.group-seating-studio"
ARTIFACTS_DIR = Path(".artifacts/classroom-planner-smoke")


def _wait_for_app_heading(page: Any) -> None:
    """Poll for the planner heading through the SPA transition after login."""

    app_heading = page.get_by_role("heading", name="Klassrumskartan", exact=True)
    for _ in range(30):
        if app_heading.count() > 0:
            return
        page.wait_for_timeout(500)

    raise AssertionError("Klassrumskartan did not render after protected-route login.")


def _login_to_app(page: Any, *, base_url: str, email: str, password: str) -> None:
    """Log in through the shared repo flow, then open the protected app route."""

    _login(page, base_url=base_url, email=email, password=password)
    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    _wait_for_app_heading(page)


def _create_roster(page: Any, *, roster_name: str) -> None:
    """Create a deterministic class list through the live roster modal."""

    create_button = page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(roster_name)))).to_be_visible()


def _create_template(page: Any, *, template_name: str) -> None:
    """Create a tiny classroom through the live room modal."""

    create_button = page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    expect(create_button).to_be_visible(timeout=60000)
    create_button.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(template_name)))).to_be_visible()


def _open_class_workspace(page: Any, *, roster_name: str) -> None:
    """Open the class workspace from the class-first landing surface."""

    roster_card = page.get_by_role("button", name=re.compile(re.escape(roster_name))).first
    expect(roster_card).to_be_visible()
    roster_card.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Välj arbetsyta", re.IGNORECASE))
    ).to_be_visible()


def _focus_workspace_mode(page: Any, *, label: str) -> None:
    """Select one compact class-workspace mode through the segmented toggle."""

    toggle = page.locator('[data-ui="segmented-toggle"]')
    toggle.get_by_role("button", name=re.compile(re.escape(label), re.IGNORECASE)).click()


def _open_grouping_history(page: Any) -> None:
    """Verify the grouping history drawer stays separate and secondary."""

    page.get_by_role("button", name=re.compile(r"Visa grupphistorik", re.IGNORECASE)).click()
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    page.get_by_role("button", name="×").click()
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).not_to_be_visible()


def _open_grouping_workspace(page: Any, *, template_name: str) -> None:
    """Open grouping directly and verify classroom support stays optional inside it."""

    _focus_workspace_mode(page, label="Grupper")
    template_select = page.get_by_role("combobox").first
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
    expect(page.get_by_text(template_name, exact=True)).to_be_visible()


def _exercise_grouping_fundamentals(page: Any) -> None:
    """Verify grouping-only randomize and explicit blank new-draft behavior."""

    first_group_name = page.locator("input[type='text']").first
    second_group_name = page.locator("input[type='text']").nth(1)
    first_group_name.fill("Handledargrupp")
    first_group_name.press("Tab")
    second_group_name.fill("Fördjupning")
    second_group_name.press("Tab")
    expect(first_group_name).to_have_value("Handledargrupp")
    expect(second_group_name).to_have_value("Fördjupning")
    expect(page.locator('[data-test="group-order-badge"]').nth(0)).to_contain_text("Ordning 1")
    expect(page.locator('[data-test="group-order-badge"]').nth(1)).to_contain_text("Ordning 2")

    page.locator('[data-test="move-group-down"]').first.click()
    expect(page.locator("input[type='text']").nth(0)).to_have_value("Fördjupning")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Handledargrupp")
    expect(page.locator('[data-test="group-order-badge"]').nth(0)).to_contain_text("Ordning 1")
    expect(page.locator('[data-test="group-order-badge"]').nth(1)).to_contain_text("Ordning 2")

    page.get_by_role("button", name=re.compile(r"Slumpa", re.IGNORECASE)).click()
    expect(page.locator("input[type='text']").nth(0)).to_have_value("Fördjupning")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Handledargrupp")
    expect(page.get_by_text("Alla elever ligger i grupp", exact=True)).to_be_visible()

    page.get_by_role("button", name=re.compile(r"Nytt grupputkast", re.IGNORECASE)).click()
    expect(first_group_name).to_have_value("Grupp 1")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Grupp 2")
    expect(page.get_by_text("Handledargrupp", exact=True)).not_to_be_visible()
    expect(page.locator("aside").get_by_text("2", exact=True)).to_be_visible()

    page.locator('[data-test="move-group-down"]').first.click()
    expect(page.locator("input[type='text']").nth(0)).to_have_value("Grupp 1")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Grupp 2")


def _open_seating_workspace(page: Any, *, template_name: str) -> None:
    """Open seating directly from the selector, then choose a room in that workspace."""

    _focus_workspace_mode(page, label="Sittplatser")
    template_select = page.get_by_role("combobox").first
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
    expect(page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE))).to_be_visible()


def _switch_seating_workspace_template(page: Any, *, template_name: str) -> None:
    """Switch room inside the same seating workspace."""

    template_select = page.get_by_role("combobox").first
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
    expect(page.get_by_text(template_name, exact=True)).to_be_visible()


def _open_student_metadata(page: Any) -> None:
    """Open one student's seating drawer to prove the planner is interactive."""

    page.get_by_role("button", name=re.compile(r"Sittplatser", re.IGNORECASE)).click()
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).click()
    expect(page.get_by_text("Elevanteckningar", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ada Lovelace", re.IGNORECASE))
    ).to_be_visible()


def _close_student_metadata(page: Any) -> None:
    """Close the student-notes drawer before background navigation checks."""

    page.get_by_role("button", name="×").click()
    expect(page.get_by_text("Elevanteckningar", exact=True)).not_to_be_visible()


def _return_to_class_workspace(page: Any) -> None:
    """Return to the class workspace without discarding the active draft."""

    _focus_workspace_mode(page, label="Översikt")
    expect(
        page.get_by_role("heading", name=re.compile(r"Välj arbetsyta", re.IGNORECASE))
    ).to_be_visible()


def _verify_seating_history_stays_empty(page: Any) -> None:
    """Ensure room switching does not silently create historical seating drafts."""

    page.get_by_role("button", name=re.compile(r"Visa sittplatshistorik", re.IGNORECASE)).click()
    expect(page.get_by_text("Ingen sittplatshistorik ännu.", exact=True)).to_be_visible()
    page.get_by_role("button", name="×").click()
    expect(page.get_by_text("Ingen sittplatshistorik ännu.", exact=True)).not_to_be_visible()


def _exit_to_landing(page: Any) -> None:
    """Leave the class workspace and land on the app entry surface."""

    _focus_workspace_mode(page, label="Sittplatser")
    page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE)).click()
    expect(page.get_by_text("Fortsätt senaste utkastet", exact=True)).to_be_visible()


def _discard_resumable_draft(page: Any, *, roster_name: str, template_name: str) -> None:
    """Use the landing-page discard action to remove the active resumable draft."""

    discard_button = page.get_by_role(
        "button",
        name=re.compile(r"Avsluta utkast", re.IGNORECASE),
    ).first
    expect(discard_button).to_be_visible(timeout=15000)
    discard_button.click(force=True)
    expect(page.get_by_text(f"{roster_name} · {template_name}")).not_to_be_visible()


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
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        _login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=first_template_name)
        _create_template(page, template_name=second_template_name)
        _open_class_workspace(page, roster_name=roster_name)
        _open_grouping_history(page)
        _open_grouping_workspace(page, template_name=first_template_name)
        _exercise_grouping_fundamentals(page)
        _return_to_class_workspace(page)
        _open_seating_workspace(page, template_name=first_template_name)
        _switch_seating_workspace_template(page, template_name=second_template_name)
        _open_student_metadata(page)
        _close_student_metadata(page)
        _return_to_class_workspace(page)
        _verify_seating_history_stays_empty(page)
        _exit_to_landing(page)
        _discard_resumable_draft(
            page,
            roster_name=roster_name,
            template_name=second_template_name,
        )

        page.screenshot(
            path=str(ARTIFACTS_DIR / "classroom-planner-smoke.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
