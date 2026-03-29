"""Dedicated live browser proof for PR-0105, PR-0106, and PR-0109 seating flow.

This script isolates the seating continuity/new-draft lifecycle from the
broader classroom-planner baseline so `PR-0105` can be verified deterministically
on the real local SPA without interference from grouping-history transitions.
It now also proves the `PR-0106` seating-only undo/redo contract and `PR-0109`
seating `Slumpa` wiring on top of the same teacher-facing continuity workflow.
The exact full-reshuffle contract for `Slumpa` remains enforced by deterministic
unit coverage; this browser proof stays focused on real UI wiring, autosave, and
undo/redo compatibility.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_classroom_planner_smoke import (
    _close_history_drawer,
    _create_roster,
    _create_template,
    _delete_remaining_historic_seating_draft,
    _open_class_workspace,
    _open_seating_workspace,
    _start_second_seating_draft,
    _switch_seating_workspace_template,
    _verify_seating_history_starts_empty,
    _verify_seating_toolbar,
)
from scripts.playwright_ui_smoke import _launch_chromium

APP_PATH = "/apps/classroom.group-seating-studio"
ARTIFACTS_DIR = Path(".artifacts/classroom-planner-smoke")


def _login_to_classroom_app(page: Any, *, base_url: str, email: str, password: str) -> None:
    """Log in through the shared dialog, then open the protected planner app."""

    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
    ).to_be_visible()

    page.goto(f"{base_url}{APP_PATH}", wait_until="networkidle")
    expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()


def _verify_new_seating_draft_requires_classroom(page: Any) -> None:
    """Prove the seating action row refuses new drafts before room selection."""

    toggle = page.locator('[data-ui="segmented-toggle"]')
    toggle.get_by_role("radio", name=re.compile(r"Sittplatser", re.IGNORECASE)).click()
    template_select = page.locator('[data-test="seating-template-select"]')
    expect(template_select).to_be_visible()
    page.locator('[data-test="new-seating-draft"]').click()
    expect(
        page.get_by_text("Välj klassrum innan du startar ett nytt sittschema.", exact=True)
    ).to_be_visible()
    expect(template_select).to_be_focused()


def _unseated_pool(page: Any) -> Any:
    """Return the live unseated-students pool in the seating workspace."""

    return page.locator("aside").filter(has=page.get_by_text("Ej placerade", exact=True)).first


def _seat_token(page: Any, label_text: str) -> Any:
    """Return one visible seat token by its current label."""

    return (
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(label_text, exact=True))
        .first
    )


def _assign_student_to_seat(page: Any, *, student_name: str, seat_id: str) -> None:
    """Create a visible seating change so historic reopen can be proven honestly."""

    student_button = _unseated_pool(page).get_by_role("button", name=re.compile(student_name))
    target_seat = _seat_token(page, seat_id)
    expect(student_button).to_be_visible()
    expect(target_seat).to_be_visible()
    student_button.drag_to(target_seat)
    expect(_unseated_pool(page).get_by_role("button", name=re.compile(student_name))).to_have_count(
        0
    )
    expect(
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(student_name, exact=True))
        .first
    ).to_be_visible()


def _wait_for_autosave(page: Any) -> None:
    """Wait through autosave so backend history is the source of truth."""

    page.wait_for_timeout(1400)
    expect(page.get_by_text("Sparad", exact=True).first).to_be_visible()


def _undo_current_seating_step(page: Any, *, student_name: str) -> None:
    """Undo one in-draft seating change and prove the seat assignment is cleared."""

    undo_button = page.locator('[data-test="undo-seating-draft"]')
    expect(undo_button).to_be_enabled()
    undo_button.click()
    expect(
        _unseated_pool(page).get_by_role("button", name=re.compile(student_name))
    ).to_be_visible()
    expect(
        page.locator('[data-test="room-seat-token"]').filter(
            has=page.get_by_text(student_name, exact=True)
        )
    ).to_have_count(0)
    expect(page.locator('[data-test="redo-seating-draft"]')).to_be_enabled()


def _redo_current_seating_step(page: Any, *, student_name: str) -> None:
    """Redo one in-draft seating change and prove the seat assignment returns."""

    redo_button = page.locator('[data-test="redo-seating-draft"]')
    expect(redo_button).to_be_enabled()
    redo_button.click()
    expect(_unseated_pool(page).get_by_role("button", name=re.compile(student_name))).to_have_count(
        0
    )
    expect(
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(student_name, exact=True))
        .first
    ).to_be_visible()


def _expect_unseated_student_count(page: Any, *, expected_count: int) -> None:
    """Assert the current unseated-students count inside the live seating pool."""

    expect(_unseated_pool(page).get_by_role("button")).to_have_count(expected_count)


def _randomize_current_seating_draft(page: Any) -> None:
    """Run seating `Slumpa` and prove it fills all available seats deterministically."""

    randomize_button = page.locator('[data-test="randomize-seating"]')
    expect(randomize_button).to_be_enabled()
    _expect_unseated_student_count(page, expected_count=1)
    randomize_button.click()
    _wait_for_autosave(page)
    _expect_unseated_student_count(page, expected_count=0)


def _undo_slumpa_step(page: Any) -> None:
    """Undo the `Slumpa` reshuffle and restore the earlier single-seat arrangement."""

    undo_button = page.locator('[data-test="undo-seating-draft"]')
    expect(undo_button).to_be_enabled()
    undo_button.click()
    _expect_unseated_student_count(page, expected_count=1)


def _redo_slumpa_step(page: Any) -> None:
    """Redo the `Slumpa` reshuffle and restore the randomized seating state."""

    redo_button = page.locator('[data-test="redo-seating-draft"]')
    expect(redo_button).to_be_enabled()
    redo_button.click()
    _expect_unseated_student_count(page, expected_count=0)


def _verify_undo_steps_do_not_pollute_continuity_drawer(page: Any) -> None:
    """Continuity must stay draft-level rather than exposing undo/redo entries."""

    page.locator('[data-test="seating-history"]').click()
    expect(page.get_by_text("Ingen sitthistorik ännu.", exact=True)).to_be_visible()
    _close_history_drawer(page, title="Sittplatser")


def _verify_template_switch_stays_outside_undo(
    page: Any, *, template_name: str, student_name: str
) -> None:
    """Changing classroom context should reset seating history instead of being undoable."""

    _switch_seating_workspace_template(page, template_name=template_name)
    expect(
        _unseated_pool(page).get_by_role("button", name=re.compile(student_name))
    ).to_be_visible()
    expect(page.locator('[data-test="undo-seating-draft"]')).to_be_disabled()
    expect(page.locator('[data-test="redo-seating-draft"]')).to_be_disabled()


def _verify_new_seating_draft_clears_assignments(page: Any, *, student_name: str) -> None:
    """Confirm a fresh seating draft resets seat assignments in the same classroom."""

    expect(
        _unseated_pool(page).get_by_role("button", name=re.compile(student_name))
    ).to_be_visible()
    expect(
        page.locator('[data-test="room-seat-token"]').filter(
            has=page.get_by_text(student_name, exact=True)
        )
    ).to_have_count(0)


def _reopen_historic_seating_draft_and_verify_assignment(page: Any, *, student_name: str) -> None:
    """Reopen the previous seating draft and prove it restores the older seat placement."""

    page.locator('[data-test="seating-history"]').click()
    aside = page.locator("aside").filter(
        has=page.get_by_role("heading", name=re.compile(r"Sittplatser", re.IGNORECASE))
    )
    expect(aside.get_by_text("Tidigare sittscheman", exact=True)).to_be_visible()
    history_button = aside.get_by_role(
        "button", name=re.compile(r"Revision \d+", re.IGNORECASE)
    ).first
    history_button.click()

    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(_unseated_pool(page).get_by_role("button", name=re.compile(student_name))).to_have_count(
        0
    )
    expect(
        page.locator('[data-test="room-seat-token"]')
        .filter(has=page.get_by_text(student_name, exact=True))
        .first
    ).to_be_visible()


def main() -> None:
    """Run the PR-0105/PR-0106 live browser proof against the local SPA."""

    config = get_config()
    timestamp = int(time.time())
    roster_name = f"PR0105 Klass {timestamp}"
    template_name = f"PR0105 Sal {timestamp}"
    template_name_secondary = f"PR0106 Sal {timestamp}"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = ARTIFACTS_DIR / "pr0105-seating-continuity-proof.png"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        _login_to_classroom_app(
            page,
            base_url=config.base_url,
            email=config.email,
            password=config.password,
        )
        expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()

        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _create_template(page, template_name=template_name_secondary)
        _open_class_workspace(page, roster_name=roster_name)
        _verify_new_seating_draft_requires_classroom(page)
        _open_seating_workspace(page, template_name=template_name)
        _verify_seating_toolbar(page)
        _verify_seating_history_starts_empty(page)
        _assign_student_to_seat(page, student_name="Ada Lovelace", seat_id="seat-1")
        _wait_for_autosave(page)
        _undo_current_seating_step(page, student_name="Ada Lovelace")
        _redo_current_seating_step(page, student_name="Ada Lovelace")
        _randomize_current_seating_draft(page)
        _undo_slumpa_step(page)
        _redo_slumpa_step(page)
        _verify_undo_steps_do_not_pollute_continuity_drawer(page)
        _start_second_seating_draft(page)
        _verify_new_seating_draft_clears_assignments(page, student_name="Ada Lovelace")
        _reopen_historic_seating_draft_and_verify_assignment(page, student_name="Ada Lovelace")
        _delete_remaining_historic_seating_draft(page)
        _verify_template_switch_stays_outside_undo(
            page,
            template_name=template_name_secondary,
            student_name="Ada Lovelace",
        )

        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    print(f"playwright-pr0105-pr0106: ok -> {screenshot_path}")


if __name__ == "__main__":
    main()
