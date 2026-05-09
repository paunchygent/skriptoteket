"""Playwright proof for PR-0311 phone room-template modal stabilization.

Purpose:
    Prove the room-template editor modal behaves deterministically on phone:
    compact sticky footer actions render on the first edit-modal visit, missing
    classroom names focus the name input with Swedish recovery copy, and touch
    placement creates and removes real seat state without leaving a ghost
    preview behind.

Relationships:
    - Uses the public Klassrumskartan guest route to avoid authenticated state.
    - Complements PR-0310 by checking the room-builder modal's touch/no-hover
      behavior instead of the simplified phone seating map.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Sequence

from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import wait_for_app_heading
from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import (
    new_private_key,
    public_key_pem,
    temporary_backend_server,
    temporary_vite_server,
)
from scripts._playwright_touch import assert_touch_action, pinch_zoom

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0311-phone-room-template-modal")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"


def _first_visible(page: Page, selector: str) -> Locator:
    """Return the first visible locator matching a selector list."""

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


def _assert_fits_viewport(page: Page, locator: Locator, *, label: str) -> None:
    """Assert a visible element is contained in the current viewport."""

    box = locator.bounding_box()
    viewport = page.viewport_size
    if box is None or viewport is None:
        raise AssertionError(f"{label} did not expose a bounding box.")
    if box["x"] < -1 or box["x"] + box["width"] > viewport["width"] + 1:
        raise AssertionError(f"{label} overflows horizontally: {box}.")
    if box["y"] < -1 or box["y"] + box["height"] > viewport["height"] + 1:
        raise AssertionError(f"{label} overflows vertically: {box}.")


def _assert_footer_one_row(page: Page) -> None:
    """Assert the compact modal footer actions fit on one phone row."""

    buttons = [
        page.locator('[data-test="room-template-delete-button"]'),
        page.locator('[data-test="room-template-cancel-button"]'),
        page.locator('[data-test="room-template-save-button"]'),
    ]
    boxes = []
    for button in buttons:
        expect(button).to_be_visible()
        boxes.append(button.bounding_box())
    if any(box is None for box in boxes):
        raise AssertionError("Room-template footer buttons did not expose boxes.")
    top_edges = [box["y"] for box in boxes if box is not None]
    if max(top_edges) - min(top_edges) > 4:
        raise AssertionError(f"Room-template footer buttons wrapped: {boxes}.")
    _assert_fits_viewport(
        page,
        page.locator(".room-template-modal-footer").first,
        label="room-template modal footer",
    )


def _open_new_template_modal(page: Page) -> None:
    """Open the create-classroom modal from the public phone overview."""

    _first_visible(
        page,
        '[data-test="overview-create-template"], [data-test="phone-overview-create-template"]',
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()


def _save_template_from_modal(page: Page, *, template_name: str) -> None:
    """Create a small classroom after the missing-name recovery check."""

    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    expect(grid_buttons.nth(0)).to_be_visible()
    grid_buttons.nth(0).tap()
    page.locator('[data-test="room-template-save-button"]').click()
    _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )


def _open_existing_template_modal(page: Page, *, template_name: str) -> None:
    """Select the created classroom and open the edit modal."""

    template_value = _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )
    select = _first_visible(
        page, '[data-test="overview-template-select"], [data-test="phone-overview-template-select"]'
    )
    select.select_option(value=template_value)
    _first_visible(
        page, '[data-test="overview-edit-template"], [data-test="phone-overview-edit-template"]'
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).to_be_visible()


def _assert_missing_name_recovery(page: Page) -> None:
    """Click save without a name and assert the recovery copy and focus target."""

    page.locator('[data-test="room-template-save-button"]').click()
    expect(page.locator('[data-test="room-template-name-error"]')).to_have_text(
        "Ge klassrummet ett namn innan du sparar."
    )
    focused_name = page.evaluate(
        "() => document.activeElement?.getAttribute('data-test') === 'room-template-name-input'"
    )
    if focused_name is not True:
        raise AssertionError("Missing-name save did not focus the classroom name input.")


def _assert_seat_touch_contract(page: Page) -> None:
    """Tap the room grid with Sittplats selected and assert real seat toggling."""

    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    cell = page.locator("section .relative.grid.gap-1 button[type='button']").nth(0)
    seat_tokens = page.locator('[data-test="room-builder-viewport"] [data-test="room-seat-token"]')
    expect(seat_tokens).to_have_count(0)
    cell.tap()
    expect(seat_tokens).to_have_count(1)
    expect(seat_tokens.first).to_contain_text(re.compile(r"plats-1", re.IGNORECASE))
    expect(page.locator('[data-test="room-builder-ghost-overlay"]')).to_have_count(0)
    cell.tap()
    expect(seat_tokens).to_have_count(0)
    expect(page.locator('[data-test="room-builder-ghost-overlay"]')).to_have_count(0)


def _assert_builder_pinch_zoom(page: Page) -> None:
    """Pinch the phone builder viewport and assert no accidental seat appears."""

    assert_touch_action(page, '[data-test="room-builder-viewport"]')
    zoom_percent = page.locator('[data-test="builder-zoom-percent"]')
    initial_zoom = zoom_percent.inner_text()
    pinch_zoom(page, '[data-test="room-builder-viewport"]')
    expect(zoom_percent).not_to_have_text(initial_zoom)
    expect(
        page.locator('[data-test="room-builder-viewport"] [data-test="room-seat-token"]')
    ).to_have_count(0)


def _run_phone_proof(page: Page, *, base_url: str) -> None:
    """Run the phone modal proof against the public route."""

    run_suffix = str(int(time.time()))
    template_name = f"PR0311 Sal {run_suffix}"
    page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)

    _open_new_template_modal(page)
    _assert_fits_viewport(
        page, page.locator('[data-test="room-template-modal-panel"]'), label="new modal"
    )
    _assert_missing_name_recovery(page)
    _assert_seat_touch_contract(page)
    _assert_builder_pinch_zoom(page)
    page.screenshot(path=str(ARTIFACTS_DIR / "phone-create-modal-recovery.png"), full_page=True)
    _save_template_from_modal(page, template_name=template_name)

    _open_existing_template_modal(page, template_name=template_name)
    expect(page.locator('[data-test="room-template-delete-button"]')).to_have_text("Radera")
    expect(page.locator('[data-test="room-template-cancel-button"]')).to_have_text("Avbryt")
    expect(page.locator('[data-test="room-template-save-button"]')).to_have_text("Spara")
    _assert_footer_one_row(page)
    page.screenshot(path=str(ARTIFACTS_DIR / "phone-edit-modal-footer.png"), full_page=True)


def _run_desktop_hover_proof(page: Page, *, base_url: str) -> None:
    """Run the desktop hover-preview preservation proof."""

    page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)
    _open_new_template_modal(page)
    page.get_by_role("button", name=re.compile(r"Whiteboard", re.IGNORECASE)).click()
    page.locator("section .relative.grid.gap-1 button[type='button']").nth(2).hover()
    expect(page.locator('[data-test="room-builder-ghost-overlay"]')).to_be_visible()
    page.screenshot(path=str(ARTIFACTS_DIR / "desktop-hover-ghost-preview.png"), full_page=True)


def _run(*, base_url: str) -> None:
    """Run the PR-0311 phone and desktop browser proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        phone_context = browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
        )
        _run_phone_proof(phone_context.new_page(), base_url=base_url)
        phone_context.close()

        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        _run_desktop_hover_proof(desktop_context.new_page(), base_url=base_url)
        desktop_context.close()
        browser.close()

    print(f"pr-0311-phone-room-template-modal: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the PR-0311 browser proof."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--start-vite", action="store_true")
    proof_args, config_argv = parser.parse_known_args(argv)
    config = get_config(config_argv)
    private_key = new_private_key()
    public_key = public_key_pem(private_key)

    if proof_args.start_backend:
        with temporary_backend_server(
            public_key,
            artifacts_dir=ARTIFACTS_DIR,
            port=None if proof_args.start_vite else 8000,
        ) as live_backend:
            if proof_args.start_vite:
                with temporary_vite_server(proxy_target=live_backend) as live_base:
                    _run(base_url=live_base)
                return
            _run(base_url=config.base_url)
        return

    if proof_args.start_vite:
        with temporary_vite_server() as live_base:
            _run(base_url=live_base)
        return

    _run(base_url=config.base_url)


if __name__ == "__main__":  # pragma: no cover
    main()
