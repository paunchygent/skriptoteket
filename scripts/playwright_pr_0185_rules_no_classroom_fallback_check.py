"""Live PR-0185 proof for the rules no-classroom fallback slice.

Purpose:
    Verify the narrowed ST-29-06 implementation against the live local SPA by
    creating one real roster with no classroom, then proving that `Regler`
    shows the approved empty-map copy, an organized off-map roster surface, and
    intact pending-rule selection feedback.

Relationships:
    - reuses shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic planner data through the real local API
    - writes screenshots under `.artifacts/pr-0185-rules-no-classroom-fallback-check/`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0185-rules-no-classroom-fallback-check")
EMPTY_STATE_COPY = (
    "Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta med "
    "regler direkt utifrån klassrummets möblering."
)
GROUPS_HINT_COPY = "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd."
STUDENTS = [
    {"id": "student-1", "display_name": "Ada Lovelace"},
    {"id": "student-2", "display_name": "Alan Turing"},
    {"id": "student-3", "display_name": "Grace Hopper"},
    {"id": "student-4", "display_name": "Hedy Lamarr"},
    {"id": "student-5", "display_name": "Katherine Johnson"},
    {"id": "student-6", "display_name": "Mary Jackson"},
    {"id": "student-7", "display_name": "Radia Perlman"},
    {"id": "student-8", "display_name": "Sophie Wilson"},
]


def _api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _login_api(*, api_base_url: str, email: str, password: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    response = session.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    csrf_token = response.json()["csrf_token"]
    return session, csrf_token


def _api_mutate(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = session.request(
        method=method,
        url=f"{api_base_url}{path}",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
        timeout=30,
    )
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def _create_roster(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_name: str,
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={"name": roster_name, "students": STUDENTS},
    )


def _prepare_workspace(api_base_url: str, email: str, password: str) -> str:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_name=f"PR0185 Klass {suffix}",
    )
    return roster["name"]


def _bounding_box(locator: Locator) -> dict[str, float]:
    box = locator.bounding_box()
    if box is None:
        raise AssertionError("Expected a visible element with a concrete bounding box.")
    return box


def _assert_organized_roster(page: Page, *, roster_name: str) -> None:
    panel = page.locator('[data-test="rules-map-unplaced"]')
    expect(panel).to_be_visible(timeout=60_000)
    expect(panel.get_by_text(roster_name, exact=True)).to_be_visible()
    expect(page.locator('[data-test="rules-map-unplaced-count"]')).to_have_text(
        f"{len(STUDENTS)} elever"
    )

    grid = page.locator('[data-test="rules-map-unplaced-grid"]')
    expect(grid).to_be_visible()
    assert grid.evaluate("element => getComputedStyle(element).display") == "grid"

    buttons = panel.locator('button[data-test^="rules-unplaced-student-"]')
    expect(buttons).to_have_count(len(STUDENTS))
    boxes = buttons.evaluate_all(
        """elements => elements.map(element => {
            const rect = element.getBoundingClientRect();
            return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
        })"""
    )

    rounded_x_positions = {round(box["x"]) for box in boxes}
    assert len(rounded_x_positions) >= 2, (
        "Expected the off-map roster to render as a multi-column organized grid "
        f"at desktop width, got x positions {sorted(rounded_x_positions)}."
    )

    first_row_y = round(boxes[0]["y"])
    same_row_count = sum(1 for box in boxes if abs(round(box["y"]) - first_row_y) <= 2)
    assert same_row_count >= 2, "Expected at least two students to share the first grid row."


def _assert_selection_feedback(page: Page) -> None:
    page.locator('[data-test="rules-tool-keep_apart"]').click()
    expect(page.locator('[data-test="rules-pending-panel"]')).to_be_visible(timeout=60_000)

    first_student = page.locator('[data-test="rules-unplaced-student-student-1"]')
    third_student = page.locator('[data-test="rules-unplaced-student-student-3"]')

    first_student.click()
    third_student.click()

    expect(page.locator('[data-test="rules-map-unplaced-selected-count"]')).to_have_text("2 valda")
    expect(page.locator('[data-test="rules-unplaced-student-order-student-1"]')).to_have_text("1")
    expect(page.locator('[data-test="rules-unplaced-student-order-student-3"]')).to_have_text("2")
    expect(page.locator('[data-test="rules-pending-panel"]')).to_contain_text("Ada Lovelace")
    expect(page.locator('[data-test="rules-pending-panel"]')).to_contain_text("Grace Hopper")
    expect(first_student).to_have_attribute("aria-pressed", "true")
    expect(third_student).to_have_attribute("aria-pressed", "true")


def _create_rule_and_assert_summary_height(page: Page) -> None:
    summary_panel = page.locator('[data-test="rules-summary-panel"]')
    height_before_rule = _bounding_box(summary_panel)["height"]

    page.locator('[data-test="rules-commit-rule"]').click()
    expect(page.locator('[data-test="rules-active-card"]')).to_have_count(1, timeout=60_000)

    height_after_rule = _bounding_box(summary_panel)["height"]
    assert abs(height_after_rule - height_before_rule) <= 6, (
        "Expected the rules summary panel to keep roughly the same height before and after the "
        f"first rule is created, got before={height_before_rule:.1f}px after={height_after_rule:.1f}px."
    )


def _assert_groups_hint(page: Page) -> None:
    focus_workspace_mode(page, label="Grupper")
    expect(page.get_by_text(GROUPS_HINT_COPY, exact=True)).to_be_visible(timeout=60_000)


def _select_no_classroom(page: Page) -> None:
    template_select = page.locator('[data-test="overview-template-select"]')
    expect(template_select).to_be_visible(timeout=60_000)
    template_select.select_option(value="")
    expect(template_select).to_have_value("")


def _assert_rules_no_classroom_state(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    roster_name: str,
    screenshot_prefix: str,
    viewport_width: int,
) -> None:
    login_to_app(page, base_url=base_url, email=email, password=password)
    open_class_workspace(page, roster_name=roster_name)
    _select_no_classroom(page)

    focus_workspace_mode(page, label="Regler")
    expect(page.locator('[data-test="rules-map-panel"]')).to_be_visible(timeout=60_000)
    expect(page.locator('[data-test="rules-map-empty-state"]')).to_have_text(EMPTY_STATE_COPY)

    _assert_organized_roster(page, roster_name=roster_name)
    _assert_selection_feedback(page)
    _create_rule_and_assert_summary_height(page)

    rules_panel = page.locator('[data-test="rules-map-panel"]')
    panel_box = _bounding_box(rules_panel)
    assert panel_box["width"] >= viewport_width * 0.48, (
        "Expected the rules map panel to remain visually dominant even without a classroom. "
        f"Got width {panel_box['width']:.1f}px at viewport {viewport_width}px."
    )

    page.screenshot(path=str(ARTIFACTS_DIR / f"{screenshot_prefix}-rules.png"), full_page=True)
    _assert_groups_hint(page)
    page.screenshot(path=str(ARTIFACTS_DIR / f"{screenshot_prefix}-groups.png"), full_page=True)


def main() -> None:
    config = get_config()
    api_base_url = _api_base_url(config.base_url)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    roster_name = _prepare_workspace(api_base_url, config.email, config.password)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        try:
            for screenshot_prefix, width, height in [
                ("desktop-1440x900", 1440, 900),
                ("laptop-1366x768", 1366, 768),
            ]:
                page = browser.new_page(viewport={"width": width, "height": height})
                try:
                    _assert_rules_no_classroom_state(
                        page,
                        base_url=config.base_url,
                        email=config.email,
                        password=config.password,
                        roster_name=roster_name,
                        screenshot_prefix=screenshot_prefix,
                        viewport_width=width,
                    )
                finally:
                    page.close()
        finally:
            browser.close()

    print("playwright-pr-0185: ok")


if __name__ == "__main__":
    main()
