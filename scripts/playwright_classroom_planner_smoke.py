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

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

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

    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    page.wait_for_timeout(750)
    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    _wait_for_app_heading(page)


def _click_landing_cta_button(page: Any, *, label_pattern: re.Pattern[str]) -> None:
    """Click a landing CTA button through transient CTA rerenders."""

    for attempt in range(3):
        cta = (
            page.locator("article")
            .filter(has=page.get_by_text("Fortsätt senaste utkastet", exact=True))
            .first
        )
        expect(cta).to_be_visible(timeout=15000)
        page.wait_for_timeout(300)
        button = page.get_by_role("button", name=label_pattern)
        expect(button).to_be_visible(timeout=15000)
        try:
            button.click(timeout=5000)
            return
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise
            page.wait_for_timeout(500)


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

    builder_viewport = page.locator('[data-test="room-builder-viewport"]')
    expect(builder_viewport).to_be_visible()
    initial_zoom = page.locator('[data-test="builder-zoom-percent"]').inner_text()
    builder_scroll_fits = builder_viewport.evaluate(
        """element => ({
            widthFits: element.scrollWidth <= element.clientWidth + 2,
            heightFits: element.scrollHeight <= element.clientHeight + 2,
        })"""
    )
    assert builder_scroll_fits["widthFits"] and builder_scroll_fits["heightFits"]

    page.locator('[data-test="builder-zoom-in"]').click()
    expect(page.locator('[data-test="builder-zoom-percent"]')).not_to_have_text(initial_zoom)
    page.locator('[data-test="builder-zoom-fit"]').click()
    expect(page.locator('[data-test="builder-zoom-percent"]')).to_have_text(initial_zoom)

    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()

    expect(builder_viewport.get_by_text("seat-1", exact=True)).to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Bänk", re.IGNORECASE)).click()
    grid_buttons.nth(15).click()
    page.locator('[data-test="builder-clear-room"]').click()
    expect(builder_viewport.get_by_text("seat-1", exact=True)).not_to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).not_to_be_visible()

    page.get_by_role("button", name=re.compile(r"Placera plats", re.IGNORECASE)).click()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    expect(builder_viewport.get_by_text("seat-1", exact=True)).to_be_visible()
    expect(builder_viewport.get_by_text("seat-2", exact=True)).to_be_visible()

    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(template_name)))).to_be_visible()


def _open_class_workspace(page: Any, *, roster_name: str) -> None:
    """Open the class workspace from the class-first landing surface."""

    roster_card = page.get_by_role("button", name=re.compile(re.escape(roster_name))).first
    expect(roster_card).to_be_visible()
    roster_card.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Klassöversikt", re.IGNORECASE))
    ).to_be_visible()


def _focus_workspace_mode(page: Any, *, label: str) -> None:
    """Select one compact class-workspace mode through the segmented toggle."""

    toggle = page.locator('[data-ui="segmented-toggle"]')
    toggle.get_by_role("button", name=re.compile(re.escape(label), re.IGNORECASE)).click()


def _open_grouping_history(page: Any) -> None:
    """Open the grouping history drawer from the grouping toolbar."""

    page.locator('[data-test="grouping-history"]').click()


def _close_history_drawer(page: Any) -> None:
    """Close the visible history drawer without hitting unrelated close buttons."""

    history_drawer = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(r"Grupper", re.IGNORECASE))
    )
    history_drawer.get_by_role("button", name="×").click()


def _verify_grouping_history_starts_empty(page: Any) -> None:
    """Verify the grouping drawer starts empty before a second draft exists."""

    _open_grouping_history(page)
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    _close_history_drawer(page)
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
    expect(template_select).to_have_value(matching_option["value"])


def _exercise_grouping_fundamentals(page: Any) -> None:
    """Verify blank grouping drafts plus browser-level undo/redo inside grouping."""

    first_group_name = page.locator("input[type='text']").first
    redo_button = page.locator('[data-test="redo-grouping"]')

    page.get_by_role("button", name=re.compile(r"Nytt grupputkast", re.IGNORECASE)).click()
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


def _start_second_grouping_draft(page: Any) -> None:
    """Create a second blank grouping draft so the first one moves to history."""

    first_group_name = page.locator("input[type='text']").first

    page.get_by_role("button", name=re.compile(r"Nytt grupputkast", re.IGNORECASE)).click()
    expect(first_group_name).to_have_value("Grupp 1")
    expect(page.locator("input[type='text']").nth(1)).to_have_value("Grupp 2")


def _reopen_historic_grouping_draft(page: Any) -> None:
    """Open the older grouping draft from the history drawer overlay."""

    _open_grouping_history(page)
    expect(page.get_by_text("Aktuellt grupputkast", exact=True)).to_be_visible()
    history_button = page.get_by_role(
        "button", name=re.compile(r"Revision \d+", re.IGNORECASE)
    ).first
    history_button.click()
    expect(page.locator("input[type='text']").first).to_have_value("Arbetslag Alfa")


def _delete_remaining_historic_grouping_draft(page: Any) -> None:
    """Delete one historic grouping draft and keep the active draft intact."""

    _open_grouping_history(page)
    initial_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    page.get_by_role("button", name="Ta bort historiskt utkast").first.click()
    expect(page.get_by_text("Ta bort utkast?", exact=True)).to_be_visible()
    page.get_by_role("button", name=re.compile(r"^Ta bort$", re.IGNORECASE)).click()
    page.wait_for_timeout(500)
    _close_history_drawer(page)
    _open_grouping_history(page)
    remaining_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    assert remaining_history_count == initial_history_count - 1
    if remaining_history_count == 0:
        expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    _close_history_drawer(page)
    expect(page.locator('[data-test="grouping-history"]')).to_be_visible()


def _open_seating_workspace(page: Any, *, template_name: str) -> None:
    """Open seating directly from the selector, then choose a room in that workspace."""

    _focus_workspace_mode(page, label="Sittplatser")
    setup_surface = page.locator('[data-test="seating-workspace-setup"]')
    expect(setup_surface).to_be_visible()
    expect(page.locator('[data-test="grouping-history"]')).to_have_count(0)
    template_select = setup_surface.get_by_role("combobox")
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
    expect(page.locator('[data-test="edit-current-template"]')).to_be_visible()


def _switch_seating_workspace_template(page: Any, *, template_name: str) -> None:
    """Switch room inside the same seating workspace."""

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
    expect(
        page.locator('[data-test="seating-workspace-setup"]').get_by_role(
            "heading",
            name=re.compile(re.escape(template_name)),
        ),
    ).to_be_visible()
    expect(page.locator('[data-test="edit-current-template"]')).to_be_visible()


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
        page.get_by_role("heading", name=re.compile(r"Klassöversikt", re.IGNORECASE))
    ).to_be_visible()


def _verify_seating_toolbar(page: Any) -> None:
    """Ensure seating exposes the intended minimal secondary action."""

    edit_classroom_button = page.locator('[data-test="edit-current-template"]')
    expect(edit_classroom_button).to_be_visible()
    expect(edit_classroom_button).to_have_text(re.compile(r"Redigera klassrum", re.IGNORECASE))


def _exit_to_landing(page: Any) -> None:
    """Leave the class workspace and land on the app entry surface."""

    page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE)).click()
    expect(page.get_by_text("Fortsätt senaste utkastet", exact=True)).to_be_visible()


def _resume_from_landing(page: Any) -> None:
    """Resume the active draft from the landing CTA."""

    _click_landing_cta_button(
        page,
        label_pattern=re.compile(r"^Fortsätt$", re.IGNORECASE),
    )
    expect(page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE))).to_be_visible()


def _dismiss_resumable_cta(page: Any, *, roster_name: str, template_name: str) -> None:
    """Dismiss the landing resumable CTA without deleting the active draft."""

    _click_landing_cta_button(
        page,
        label_pattern=re.compile(r"^Stäng senaste utkastet$", re.IGNORECASE),
    )
    expect(page.get_by_text("Fortsätt senaste utkastet", exact=True)).not_to_be_visible()
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
        _open_grouping_workspace(page, template_name=first_template_name)
        _verify_grouping_history_starts_empty(page)
        _exercise_grouping_fundamentals(page)
        _start_second_grouping_draft(page)
        _reopen_historic_grouping_draft(page)
        _delete_remaining_historic_grouping_draft(page)
        expect(page.locator("input[type='text']").first).to_have_value("Arbetslag Alfa")
        _open_seating_workspace(page, template_name=first_template_name)
        _switch_seating_workspace_template(page, template_name=second_template_name)
        _verify_seating_toolbar(page)
        _open_student_metadata(page)
        _close_student_metadata(page)
        _return_to_class_workspace(page)
        _exit_to_landing(page)
        _resume_from_landing(page)
        _exit_to_landing(page)
        _dismiss_resumable_cta(page, roster_name=roster_name, template_name=second_template_name)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "classroom-planner-smoke.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
