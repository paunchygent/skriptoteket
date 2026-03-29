"""Live proof for PR-0157 dense planner/editor toolbars.

Verifies the shared dense-tool primitives on the two proving grounds for this
slice:

- planner seating toolbar at `/apps/classroom.group-seating-studio`
- editor workspace toolbar at `/admin/tools/:toolId`

Artifacts are written under `.artifacts/pr-0157-live-check/`.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def _api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return f"{parsed.scheme}://{parsed.netloc}"


def main() -> None:
    config = get_config()
    api_base = _api_base_url(config.base_url)

    artifacts_dir = Path(".artifacts/pr-0157-live-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    login = session.post(
        f"{api_base}/api/v1/auth/login",
        json={"email": config.email, "password": config.password},
        timeout=30,
    )
    login.raise_for_status()

    admin_tools = session.get(f"{api_base}/api/v1/admin/tools", timeout=30)
    admin_tools.raise_for_status()
    tools = admin_tools.json().get("tools", [])
    if not tools:
        raise SystemExit("No admin tools available for editor toolbar proof.")
    tool_id = tools[0]["id"]

    session_cookie = session.cookies.get("skriptoteket_session")
    if not session_cookie:
        raise SystemExit("Missing skriptoteket_session cookie after login.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_cookies(
            [
                {
                    "name": "skriptoteket_session",
                    "value": session_cookie,
                    "domain": "127.0.0.1",
                    "path": "/",
                    "httpOnly": True,
                }
            ]
        )

        planner_page = context.new_page()
        planner_page.goto(
            f"{config.base_url}/apps/classroom.group-seating-studio",
            wait_until="networkidle",
        )
        roster_select = planner_page.locator('[data-test="overview-roster-select"]')
        expect(roster_select).to_be_visible()
        option_rows = roster_select.evaluate(
            """element => Array.from(element.options).map(option => ({
                value: option.value,
                label: option.label,
            }))"""
        )
        chosen = next((option for option in option_rows if option["value"]), None)
        if not chosen:
            raise SystemExit("No selectable roster found for planner proof.")
        roster_select.select_option(chosen["value"])
        expect(planner_page.locator('[data-ui="segmented-toggle"]')).to_be_visible()
        planner_page.get_by_role("radio", name="Sittplatser").click()
        expect(planner_page.locator('[data-test="undo-seating-draft"]')).to_be_visible()
        expect(planner_page.locator('[data-test="redo-seating-draft"]')).to_be_visible()
        expect(planner_page.locator('[data-test="seating-history-cluster"]')).to_be_visible()
        expect(planner_page.locator('[data-test="randomize-seating"]')).to_be_visible()
        expect(planner_page.locator('[data-test="seating-open-rules"]')).to_be_visible()
        expect(planner_page.locator('[data-test="seating-use-history-toggle"]')).to_be_visible()
        expect(planner_page.locator('[data-test="seating-export-default"]')).to_be_visible()
        expect(planner_page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
        seating_select = planner_page.locator('[data-test="seating-template-select"]')
        expect(seating_select).to_be_visible()
        seating_select_box = seating_select.bounding_box()
        undo_seating_box = planner_page.locator('[data-test="undo-seating-draft"]').bounding_box()
        seating_overflow_box = planner_page.locator(
            '[data-test="seating-actions-menu"]'
        ).bounding_box()
        if not seating_select_box or not undo_seating_box or not seating_overflow_box:
            raise SystemExit("Missing seating toolbar geometry for dense toolbar proof.")
        if abs(seating_select_box["height"] - undo_seating_box["height"]) > 2:
            raise SystemExit(
                f"Seating toolbar mismatch: select height {seating_select_box['height']} vs "
                f"undo height {undo_seating_box['height']}"
            )
        if abs(seating_select_box["height"] - seating_overflow_box["height"]) > 2:
            raise SystemExit(
                f"Seating toolbar mismatch: select height {seating_select_box['height']} vs "
                f"overflow height {seating_overflow_box['height']}"
            )
        planner_page.screenshot(
            path=str(artifacts_dir / "planner-seating-toolbar.png"),
            full_page=True,
        )

        planner_page.get_by_role("radio", name="Grupper").click()
        grouping_select = planner_page.locator('[data-test="grouping-template-select"]')
        expect(grouping_select).to_be_visible()
        expect(planner_page.locator('[data-test="grouping-history-cluster"]')).to_be_visible()
        expect(planner_page.locator('[data-test="undo-grouping"]')).to_be_visible()
        expect(planner_page.locator('[data-test="redo-grouping"]')).to_be_visible()
        expect(planner_page.locator('[data-test="grouping-group-count-control"]')).to_be_visible()
        expect(planner_page.locator('[data-test="group-count-value"]')).to_be_visible()
        expect(planner_page.locator('[data-test="increment-group-count"]')).to_be_visible()
        expect(planner_page.locator('[data-test="decrement-group-count"]')).to_be_visible()
        expect(planner_page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()
        grouping_select_box = grouping_select.bounding_box()
        grouping_count_box = planner_page.locator(
            '[data-test="grouping-group-count-control"]'
        ).bounding_box()
        undo_grouping_box = planner_page.locator('[data-test="undo-grouping"]').bounding_box()
        grouping_overflow_box = planner_page.locator(
            '[data-test="grouping-actions-menu"]'
        ).bounding_box()
        if (
            not grouping_select_box
            or not grouping_count_box
            or not undo_grouping_box
            or not grouping_overflow_box
        ):
            raise SystemExit("Missing grouping toolbar geometry for dense toolbar proof.")
        if abs(grouping_select_box["height"] - undo_grouping_box["height"]) > 2:
            raise SystemExit(
                f"Grouping toolbar mismatch: select height {grouping_select_box['height']} vs "
                f"undo height {undo_grouping_box['height']}"
            )
        if abs(grouping_select_box["height"] - grouping_overflow_box["height"]) > 2:
            raise SystemExit(
                f"Grouping toolbar mismatch: select height {grouping_select_box['height']} vs "
                f"overflow height {grouping_overflow_box['height']}"
            )
        if abs(grouping_select_box["y"] - grouping_count_box["y"]) > 2:
            raise SystemExit(
                f"Grouping toolbar wrapped: select row y {grouping_select_box['y']} vs "
                f"group-count row y {grouping_count_box['y']}"
            )
        planner_page.screenshot(
            path=str(artifacts_dir / "planner-grouping-toolbar.png"),
            full_page=True,
        )

        editor_page = context.new_page()
        editor_page.goto(f"{config.base_url}/admin/tools/{tool_id}", wait_until="networkidle")
        expect(editor_page.get_by_role("button", name="Spara/Öppna")).to_be_visible()
        expect(editor_page.get_by_role("button", name="Verktyg")).to_be_visible()
        expect(editor_page.get_by_role("radiogroup", name="Välj editor-läge")).to_be_visible()
        editor_page.screenshot(
            path=str(artifacts_dir / "editor-toolbar.png"),
            full_page=True,
        )

        browser.close()

    print("pr-0157-live-check: ok")


if __name__ == "__main__":
    main()
