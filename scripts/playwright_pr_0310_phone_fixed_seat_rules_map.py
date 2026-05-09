"""Playwright proof for PR-0310 phone fixed-seat rules map.

Purpose:
    Exercise the public Klassrumskartan guest route at an iPhone 15 Pro
    viewport and prove that phone `Fast plats` rule authoring exposes a compact
    classroom-seat map backed by the active template.

Relationships:
    - Uses browser-owned public guest data so no authenticated session is
      required.
    - Reuses shared Klassrumskartan workspace-mode helpers.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Sequence

from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import focus_workspace_mode, wait_for_app_heading
from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import (
    new_private_key,
    public_key_pem,
    temporary_backend_server,
    temporary_vite_server,
)
from scripts._playwright_touch import assert_touch_action, pinch_zoom

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0310-phone-fixed-seat-rules-map")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"


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


def _assert_touch_target(locator: Locator, *, label: str) -> None:
    """Assert that a visible target is large enough for phone touch selection."""

    box = locator.bounding_box()
    if box is None:
        raise AssertionError(f"{label} did not expose a visible bounding box.")
    if box["width"] < 40 or box["height"] < 40:
        raise AssertionError(f"{label} touch target too small: {box['width']}x{box['height']}.")


def _assert_marker_avoids_seat_core(*, marker: Locator, seat: Locator, label: str) -> None:
    """Assert that a compact rule marker does not cover the seat's central label lane."""

    marker_box = marker.bounding_box()
    seat_box = seat.bounding_box()
    if marker_box is None or seat_box is None:
        raise AssertionError(f"{label} did not expose visible marker and seat boxes.")
    seat_core = {
        "x": seat_box["x"] + seat_box["width"] * 0.2,
        "y": seat_box["y"] + seat_box["height"] * 0.28,
        "width": seat_box["width"] * 0.6,
        "height": seat_box["height"] * 0.5,
    }
    overlaps_core = not (
        marker_box["x"] + marker_box["width"] <= seat_core["x"]
        or marker_box["x"] >= seat_core["x"] + seat_core["width"]
        or marker_box["y"] + marker_box["height"] <= seat_core["y"]
        or marker_box["y"] >= seat_core["y"] + seat_core["height"]
    )
    if overlaps_core:
        raise AssertionError(f"{label} marker overlaps the seat label core.")


def _assert_phone_map_pinch_changed_zoom(page: Page) -> None:
    """Assert the shared phone classroom map responds to a pinch gesture."""

    map_selector = (
        '[data-test="phone-classroom-seat-map"], '
        '[data-test="phone-fixed-seat-map"], '
        '[data-test="phone-seating-workspace-canvas"]'
    )
    assert_touch_action(page, map_selector)
    zoom_percent = page.locator('[data-test="phone-fixed-seat-map-zoom-percent"]').first
    initial_zoom = zoom_percent.inner_text()
    pinch_zoom(page, map_selector)
    expect(zoom_percent).not_to_have_text(initial_zoom)


def _create_roster(page: Page, *, roster_name: str) -> None:
    """Create one browser-owned public roster through the overview UI."""

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
    """Create one browser-owned public classroom with two physical seats."""

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


def _select_overview_assets(page: Page, *, roster_name: str, template_name: str) -> None:
    """Select the public roster and classroom in the overview controls."""

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
    roster_select = _first_visible(
        page, '[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]'
    )
    template_select = _first_visible(
        page, '[data-test="overview-template-select"], [data-test="phone-overview-template-select"]'
    )
    roster_select.select_option(value=roster_value)
    template_select.select_option(value=template_value)
    expect(roster_select).to_have_value(roster_value)
    expect(template_select).to_have_value(template_value)


def _run(*, base_url: str) -> None:
    """Run the PR-0310 phone fixed-seat map proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_suffix = str(int(time.time()))
    roster_name = f"PR0310 Klass {run_suffix}"
    template_name = f"PR0310 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()

        page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _select_overview_assets(page, roster_name=roster_name, template_name=template_name)

        focus_workspace_mode(page, label="Regler")
        expect(page.locator('[data-test="phone-rules-workspace"]')).to_be_visible()
        page.locator('[data-test="phone-rules-tool-fixed_seat"]').click()
        expect(page.locator('[data-test="phone-fixed-seat-map"]')).to_be_visible()
        expect(page.locator('[data-test="phone-rules-selection"]')).to_have_count(0)
        _assert_touch_target(
            page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]'),
            label="phone fixed-seat map seat",
        )

        page.locator('[data-test="phone-rules-student-pool"]').get_by_role(
            "button", name=re.compile(r"Ada Lovelace")
        ).click()
        _assert_phone_map_pinch_changed_zoom(page)
        page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]').click()
        expect(page.locator('[data-test="phone-fixed-seat-pending-seat"]')).to_contain_text(
            "Välj en plats"
        )
        page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]').click()
        expect(page.locator('[data-test="phone-fixed-seat-pending-student"]')).to_contain_text(
            "Ada Lovelace"
        )
        expect(page.locator('[data-test="phone-fixed-seat-pending-seat"]')).to_contain_text(
            "plats-1"
        )
        expect(page.locator('[data-test="phone-rules-commit-fixed-seat"]')).to_be_enabled()
        page.screenshot(path=str(ARTIFACTS_DIR / "phone-fixed-seat-map.png"), full_page=True)

        page.locator('[data-test="phone-rules-commit-fixed-seat"]').click()
        seat = page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]')
        expect(seat).to_have_class(re.compile(r"planner-phone-fixed-seat-map-seat-fixed"))
        fixed_marker = page.locator(
            '[data-test="phone-seat-rule-marker-seat-1-fixed-seat-warning"]'
        )
        expect(fixed_marker).to_be_visible()
        _assert_marker_avoids_seat_core(
            marker=fixed_marker,
            seat=seat,
            label="phone fixed-seat saved-rule marker",
        )
        focus_workspace_mode(page, label="Sittplatser")
        page.locator('[data-test="randomize-seating"]').click()
        expect(
            page.locator(".toast").filter(
                has_text="Smart placering klar, men 2 elever fick ingen plats."
            )
        ).to_be_visible(timeout=15_000)
        occupied_seat = page.locator('[data-test="phone-fixed-seat-map-seat-seat-1"]')
        expect(occupied_seat).to_contain_text("Ada")
        _assert_phone_map_pinch_changed_zoom(page)
        occupied_seat.click()
        expect(occupied_seat).to_contain_text("Ada")
        page.screenshot(
            path=str(ARTIFACTS_DIR / "phone-capacity-shortfall-toast.png"),
            full_page=True,
        )

        focus_workspace_mode(page, label="Regler")
        page.locator('[data-test="phone-rules-tool-keep_near"]').click()
        expect(page.locator('[data-test="phone-fixed-seat-map"]')).to_have_count(0)
        expect(page.locator('[data-test="phone-rules-selection"]')).to_be_visible()
        page.screenshot(
            path=str(ARTIFACTS_DIR / "phone-relationship-rule-selection.png"),
            full_page=True,
        )
        context.close()
        browser.close()

    print(f"pr-0310-phone-fixed-seat-rules-map: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the PR-0310 browser proof."""

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
