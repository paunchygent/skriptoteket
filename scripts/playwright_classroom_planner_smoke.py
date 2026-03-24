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

from scripts._playwright_classroom_planner import (
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/classroom-planner-smoke")


def _open_grouping_history(page: Any) -> None:
    """Open the grouping history drawer from the grouping toolbar."""

    page.locator('[data-test="grouping-actions-menu"]').click()
    page.locator('[data-test="grouping-history"]').click()


def _close_history_drawer(page: Any, *, title: str) -> None:
    """Close one visible history drawer without hitting unrelated close buttons."""

    history_drawer = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(re.escape(title), re.IGNORECASE))
    )
    if history_drawer.count() == 0 or not history_drawer.first.is_visible():
        return
    history_drawer.get_by_role("button", name="×").click()


def _verify_grouping_history_starts_empty(page: Any) -> None:
    """Verify the grouping drawer starts empty before a second draft exists."""

    _open_grouping_history(page)
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    _close_history_drawer(page, title="Grupper")
    expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).not_to_be_visible()


def _open_grouping_workspace(page: Any, *, template_name: str) -> None:
    """Open grouping directly and verify classroom support stays optional inside it."""

    focus_workspace_mode(page, label="Grupper")
    template_select = page.locator('[data-test="grouping-template-select"]')
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
    _open_grouping_history(page)
    expect(page.get_by_text("Aktivt nu", exact=True)).to_be_visible()
    _close_history_drawer(page, title="Grupper")


def _delete_remaining_historic_grouping_draft(page: Any) -> None:
    """Delete one historic grouping draft and keep the active draft intact."""

    _open_grouping_history(page)
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
    _open_grouping_history(page)
    remaining_history_count = page.get_by_role("button", name="Ta bort historiskt utkast").count()
    assert remaining_history_count == initial_history_count - 1
    if remaining_history_count == 0:
        expect(page.get_by_text("Ingen grupphistorik ännu.", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    _close_history_drawer(page, title="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()


def _open_seating_workspace(page: Any, *, template_name: str) -> None:
    """Open seating directly from the selector, then choose a room in that workspace."""

    focus_workspace_mode(page, label="Sittplatser")
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
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


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
    expect(template_select).to_have_value(matching_option["value"])
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


def _open_student_metadata(page: Any) -> None:
    """Open one student's seating drawer to prove the planner is interactive."""

    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).first.click()
    expect(page.get_by_text("Elevanteckningar", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ada Lovelace", re.IGNORECASE))
    ).to_be_visible()


def _close_student_metadata(page: Any) -> None:
    """Close the student-notes drawer before background navigation checks."""

    metadata_drawer = page.locator("aside").filter(
        has=page.get_by_text("Elevanteckningar", exact=True)
    )
    metadata_drawer.get_by_role("button", name="×").click()
    expect(page.get_by_text("Elevanteckningar", exact=True)).not_to_be_visible()


def _return_to_class_workspace(page: Any) -> None:
    """Return to the class workspace without discarding the active draft."""

    focus_workspace_mode(page, label="Översikt")
    expect(
        page.get_by_role("heading", name=re.compile(r"Klassarbetsyta", re.IGNORECASE))
    ).to_be_visible()
    expect(page.locator('[data-ui="segmented-toggle"]')).to_be_visible()


def _verify_seating_toolbar(page: Any) -> None:
    """Ensure seating exposes the intended continuity, history, and classroom actions."""

    undo_button = page.locator('[data-test="undo-seating-draft"]')
    expect(undo_button).to_be_visible()
    expect(undo_button).to_have_attribute("aria-label", re.compile(r"Ångra", re.IGNORECASE))
    redo_button = page.locator('[data-test="redo-seating-draft"]')
    expect(redo_button).to_be_visible()
    expect(redo_button).to_have_attribute("aria-label", re.compile(r"Gör om", re.IGNORECASE))
    seating_actions_menu = page.locator('[data-test="seating-actions-menu"]')
    expect(seating_actions_menu).to_be_visible()
    new_seating_button = page.locator('[data-test="new-seating-draft"]')
    expect(new_seating_button).to_be_visible()
    expect(new_seating_button).to_have_text(re.compile(r"Nytt sittschema", re.IGNORECASE))
    seating_actions_menu.click()
    edit_classroom_button = page.locator('[data-test="edit-current-template"]')
    expect(edit_classroom_button).to_be_visible()
    expect(edit_classroom_button).to_have_text(re.compile(r"Redigera klassrum", re.IGNORECASE))
    seating_actions_menu.click()


def _verify_seating_zoom_and_assignment(page: Any) -> None:
    """Verify seating zoom parity and one real seat assignment while zoomed."""

    seating_viewport = page.locator('[data-test="room-canvas-viewport"]')
    seating_zoom_percent = page.locator('[data-test="seating-zoom-percent"]')
    expect(seating_viewport).to_be_visible()
    expect(seating_zoom_percent).to_be_visible()

    initial_zoom = seating_zoom_percent.inner_text()
    seating_scroll_fits = seating_viewport.evaluate(
        """element => ({
            widthFits: element.scrollWidth <= element.clientWidth + 2,
            heightFits: element.scrollHeight <= element.clientHeight + 2,
        })"""
    )
    assert seating_scroll_fits["widthFits"] and seating_scroll_fits["heightFits"]

    page.locator('[data-test="seating-zoom-in"]').click()
    expect(seating_zoom_percent).not_to_have_text(initial_zoom)
    zoomed_in = seating_zoom_percent.inner_text()
    expect(seating_viewport).to_have_js_property("scrollLeft", 0)
    viewport_box = seating_viewport.bounding_box()
    seat_box = page.locator('[data-test="room-seat-token"]').first.bounding_box()
    assert viewport_box is not None
    assert seat_box is not None
    assert seat_box["x"] >= viewport_box["x"] - 1

    seat_drop_target = (
        page.locator('[data-test="room-seat-token"]')
        .filter(has_text=re.compile(r"seat-1", re.IGNORECASE))
        .locator("xpath=ancestor::div[contains(@class, 'absolute')][1]")
    )
    data_transfer = page.evaluate_handle("new DataTransfer()")
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).dispatch_event(
        "dragstart",
        {"dataTransfer": data_transfer},
    )
    seat_drop_target.dispatch_event("dragover", {"dataTransfer": data_transfer})
    seat_drop_target.dispatch_event("drop", {"dataTransfer": data_transfer})
    expect(page.locator('[data-test="room-seat-token"]').first).to_contain_text(
        re.compile(r"Ada Lovelace", re.IGNORECASE)
    )

    page.locator('[data-test="seating-zoom-out"]').click()
    expect(seating_zoom_percent).not_to_have_text(zoomed_in)
    page.locator('[data-test="seating-zoom-fit"]').click()
    expect(seating_zoom_percent).to_have_text(initial_zoom)

    page.locator('[data-test="room-seat-token"]').first.click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ada Lovelace", re.IGNORECASE))
    ).to_be_visible()


def _open_seating_history(page: Any) -> None:
    """Open the seating history drawer from the seating toolbar."""

    page.locator('[data-test="seating-actions-menu"]').click()
    page.locator('[data-test="seating-history"]').click()


def _verify_seating_history_starts_empty(page: Any) -> None:
    """Verify the seating drawer starts empty before a second draft exists."""

    _open_seating_history(page)
    expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).to_be_visible()
    _close_history_drawer(page, title="Sittplatser")
    expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).not_to_be_visible()


def _start_second_seating_draft(page: Any) -> None:
    """Create a second seating draft in the current classroom."""

    page.locator('[data-test="new-seating-draft"]').click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    page.wait_for_timeout(500)


def _reopen_historic_seating_draft(page: Any) -> None:
    """Open the older seating draft from the seating history drawer."""

    _open_seating_history(page)
    aside = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(r"Sittplatser", re.IGNORECASE))
    )
    expect(aside.get_by_text("Tidigare sittscheman", exact=True)).to_be_visible()
    expect(aside.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    history_button = aside.get_by_role(
        "button", name=re.compile(r"Revision \d+", re.IGNORECASE)
    ).first
    history_button.click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
    _open_seating_history(page)
    expect(page.get_by_text("Aktivt nu", exact=True)).to_be_visible()
    _close_history_drawer(page, title="Sittplatser")


def _delete_remaining_historic_seating_draft(page: Any) -> None:
    """Delete one historic seating draft and keep the active one intact."""

    _open_seating_history(page)
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
    page.wait_for_timeout(300)

    remaining_history_count = initial_history_count
    for _ in range(10):
        _open_seating_history(page)
        remaining_history_count = page.get_by_role(
            "button", name="Ta bort historiskt utkast"
        ).count()
        if remaining_history_count == initial_history_count - 1:
            break
        _close_history_drawer(page, title="Sittplatser")
        page.wait_for_timeout(300)

    assert remaining_history_count == initial_history_count - 1
    if remaining_history_count == 0:
        expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Ta bort historiskt utkast").first).to_be_visible()
    _close_history_drawer(page, title="Sittplatser")
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()


def _exit_to_origin(page: Any) -> None:
    """Leave the class workspace and land on the current planner origin."""

    page.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r"/browse(?:\?.*)?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))).to_be_visible()


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

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=first_template_name)
        create_template(page, template_name=second_template_name)
        open_class_workspace(page, roster_name=roster_name)
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
        _verify_seating_zoom_and_assignment(page)
        _verify_seating_history_starts_empty(page)
        _start_second_seating_draft(page)
        _reopen_historic_seating_draft(page)
        _delete_remaining_historic_seating_draft(page)
        _open_student_metadata(page)
        _close_student_metadata(page)
        _return_to_class_workspace(page)
        _exit_to_origin(page)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "classroom-planner-smoke.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
