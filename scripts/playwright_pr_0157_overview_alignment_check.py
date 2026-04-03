"""Live PR-0157 proof for Klassrumskartan overview panel alignment.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


Purpose:
    Verify the live `Översikt` surface after the dense-tool/panel compression
    pass so the roster and classroom panels stay perfectly aligned, the two
    overview edit actions both use the shortened `Redigera` copy, and the
    primary workspace mode selector stays visually more prominent than the
    quieter overview footer actions.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/overview helpers from
      `scripts._playwright_classroom_planner`
    - seeds deterministic roster/template data through the real local API
    - writes screenshots under `.artifacts/pr-0157-overview-alignment-check/`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Locator, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import login_to_app, open_class_workspace
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0157-overview-alignment-check")


def _api_base_url(base_url: str) -> str:
    """Map the Vite dev host to the local API host for deterministic seeding."""

    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _login_api(*, api_base_url: str, email: str, password: str) -> tuple[requests.Session, str]:
    """Create an authenticated API session for local planner fixture setup."""

    session = requests.Session()
    response = session.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return session, response.json()["csrf_token"]


def _api_mutate(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    method: str,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute a CSRF-protected planner mutation against the live local API."""

    response = session.request(
        method=method,
        url=f"{api_base_url}{path}",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _create_roster(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_name: str,
) -> dict[str, Any]:
    """Seed a deterministic roster for the live overview proof."""

    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={
            "name": roster_name,
            "students": [
                {"id": "student-1", "display_name": "Ada Lovelace"},
                {"id": "student-2", "display_name": "Bo Berg"},
            ],
        },
    )


def _create_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    template_name: str,
) -> dict[str, Any]:
    """Seed a tiny classroom template for the live overview preview proof."""

    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={
            "name": template_name,
            "grid_cols": 5,
            "grid_rows": 3,
            "seats": [
                {"id": "seat-1", "x": 0, "y": 0, "zone": "front"},
                {"id": "seat-2", "x": 120, "y": 0, "zone": "front"},
            ],
            "fixtures": [],
        },
    )


def _bounding_box(locator: Locator) -> dict[str, float]:
    """Return a concrete bounding box for an element that must be visible."""

    box = locator.bounding_box()
    if box is None:
        raise AssertionError("Expected a visible element with a concrete bounding box.")
    return box


def _assert_aligned(name: str, left: float, right: float, *, tolerance: float = 1.5) -> None:
    """Assert two layout measurements stay within a strict visual tolerance."""

    if abs(left - right) > tolerance:
        raise AssertionError(f"{name} drifted: {left:.2f}px vs {right:.2f}px.")


def _select_template(page: Any, *, template_name: str) -> None:
    """Select the seeded template through the overview classroom selector."""

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


def main() -> None:
    """Run the live overview alignment proof and write screenshots to disk."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _api_base_url(base_url)
    email = config.email
    password = config.password

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    roster_name = f"PR0157 Klass {uuid4().hex[:6]}"
    template_name = f"PR0157 Sal {uuid4().hex[:6]}"

    session, csrf_token = _login_api(
        api_base_url=api_base_url,
        email=email,
        password=password,
    )
    _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_name=roster_name,
    )
    _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        template_name=template_name,
    )

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1512, "height": 982})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=email, password=password)
        open_class_workspace(page, roster_name=roster_name)
        _select_template(page, template_name=template_name)
        expect(page.locator('[data-test="overview-classroom-preview"]')).to_be_visible()
        page.wait_for_timeout(400)

        roster_panel = page.locator('[data-test="overview-roster-panel"]')
        template_panel = page.locator('[data-test="overview-template-panel"]')
        roster_select = page.locator('[data-test="overview-roster-select"]')
        template_select = page.locator('[data-test="overview-template-select"]')
        roster_preview = page.locator('[data-test="overview-roster-preview"]')
        template_preview = page.locator('[data-test="overview-classroom-preview"]')
        workspace_switch = page.locator('[data-test="planner-workspace-switch"]')
        active_workspace_button = page.locator('[data-test="planner-mode-overview"]')
        grouping_workspace_button = page.locator('[data-test="planner-mode-grouping"]')
        seating_workspace_button = page.locator('[data-test="planner-mode-seating"]')
        rules_workspace_button = page.locator('[data-test="planner-mode-rules"]')
        edit_roster_button = page.locator('[data-test="overview-edit-roster"]')
        edit_template_button = page.locator('[data-test="overview-edit-template"]')
        create_roster_button = page.get_by_role("button", name="Ny klasslista", exact=True)
        create_template_button = page.get_by_role("button", name="Nytt klassrum", exact=True)

        expect(edit_roster_button).to_have_text("Redigera")
        expect(edit_template_button).to_have_text("Redigera")
        expect(active_workspace_button).to_have_attribute("aria-checked", "true")
        for button in [grouping_workspace_button, seating_workspace_button, rules_workspace_button]:
            border_left_width = button.evaluate(
                "element => window.getComputedStyle(element).borderLeftWidth"
            )
            if border_left_width == "0px":
                raise AssertionError("Workspace switch lost an interior divider.")

        roster_panel_box = _bounding_box(roster_panel)
        template_panel_box = _bounding_box(template_panel)
        roster_select_box = _bounding_box(roster_select)
        template_select_box = _bounding_box(template_select)
        roster_preview_box = _bounding_box(roster_preview)
        template_preview_box = _bounding_box(template_preview)
        workspace_switch_box = _bounding_box(workspace_switch)
        active_workspace_box = _bounding_box(active_workspace_button)
        create_roster_box = _bounding_box(create_roster_button)
        create_template_box = _bounding_box(create_template_button)
        edit_roster_box = _bounding_box(edit_roster_button)
        edit_template_box = _bounding_box(edit_template_button)

        _assert_aligned("overview panel top edge", roster_panel_box["y"], template_panel_box["y"])
        _assert_aligned(
            "overview panel height",
            roster_panel_box["height"],
            template_panel_box["height"],
            tolerance=2.0,
        )
        _assert_aligned(
            "overview selector top edge", roster_select_box["y"], template_select_box["y"]
        )
        _assert_aligned(
            "overview selector height", roster_select_box["height"], template_select_box["height"]
        )
        _assert_aligned(
            "overview preview top edge", roster_preview_box["y"], template_preview_box["y"]
        )
        _assert_aligned(
            "overview preview height", roster_preview_box["height"], template_preview_box["height"]
        )
        _assert_aligned(
            "overview footer primary top edge", create_roster_box["y"], create_template_box["y"]
        )
        _assert_aligned(
            "overview footer primary height",
            create_roster_box["height"],
            create_template_box["height"],
        )
        _assert_aligned(
            "overview footer edit top edge", edit_roster_box["y"], edit_template_box["y"]
        )
        _assert_aligned(
            "overview footer edit height", edit_roster_box["height"], edit_template_box["height"]
        )
        if active_workspace_box["height"] <= create_roster_box["height"]:
            raise AssertionError(
                "Primary workspace selector drifted below overview footer action height."
            )
        if workspace_switch_box["height"] <= create_roster_box["height"]:
            raise AssertionError(
                "Workspace switch shell drifted below overview footer action height."
            )

        page.screenshot(path=str(ARTIFACTS_DIR / "overview-panels.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright overview alignment proof screenshots written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
