"""Playwright proof for PR-0303 public guest overview distribution wiring.

Purpose:
    Exercise the public Klassrumskartan guest route in a live browser and prove
    that overview `Dela och exportera` uses the selected browser-owned class
    list/classroom draft state. The proof also verifies that a link created in
    the workspace remains visible when the user returns to overview.

Relationships:
    - Uses the public guest route only; no authenticated session is required.
    - Intercepts only the public share/export helper endpoints so the proof can
      assert request snapshots without depending on renderer binary output.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Sequence

from playwright.sync_api import Locator, Page, Route, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import focus_workspace_mode, wait_for_app_heading
from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import temporary_vite_server

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0303-public-guest-overview-distribution")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"


def _visible(locator: Locator) -> bool:
    """Return whether any matched element is currently visible."""

    for index in range(locator.count()):
        if locator.nth(index).is_visible():
            return True
    return False


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
    """Create one browser-owned public classroom through the overview UI."""

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
    page.get_by_role("button", name=re.compile(r"Skapa(?: klassrum)?", re.IGNORECASE)).click()
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


def _install_public_distribution_routes(page: Page) -> dict[str, list[dict[str, Any]]]:
    """Capture public share/export helper payloads and return deterministic results."""

    captured: dict[str, list[dict[str, Any]]] = {"share": [], "export": []}

    def share_handler(route: Route) -> None:
        payload = route.request.post_data_json
        if not isinstance(payload, dict):
            payload = json.loads(route.request.post_data or "{}")
        match = re.search(r"/(grouping|seating)/share$", route.request.url)
        kind = match.group(1) if match else "unknown"
        payload = {**payload, "__kind": kind}
        captured["share"].append(payload)
        share_number = len(captured["share"])
        artifact = {
            "id": f"pr-0303-share-{share_number}",
            "title": f"PR0303 {kind} delad länk {share_number}",
            "draft_kind": kind,
            "source": "public_guest",
            "source_revision": payload["expected_revision"],
            "slug": f"pr0303-{share_number}",
            "public_path": f"/share/classroom/pr0303/{share_number}",
            "public_url": f"https://skriptoteket.example/share/classroom/pr0303/{share_number}",
            "preview_description": "PR-0303 public guest proof",
            "renderer_version": "klassrumskartan-share-renderer-v1",
            "presentation_schema_version": "grouping-share-v1",
            "content_hash": f"sha256:content-{share_number}",
            "presentation_hash": f"sha256:presentation-{share_number}",
            "created_at": "2026-05-06T08:00:00Z",
            "updated_at": "2026-05-06T08:00:00Z",
            "revoked_at": None,
            "expires_at": "2026-06-06T08:00:00Z",
        }
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "artifact": artifact,
                    "public_path": artifact["public_path"],
                    "public_url": artifact["public_url"],
                    "public_revoke_secret": payload["revoke_secret"],
                    "superseded_previous": False,
                    "reused_client_operation": False,
                }
            ),
        )

    def export_handler(route: Route) -> None:
        payload = route.request.post_data_json
        if not isinstance(payload, dict):
            payload = json.loads(route.request.post_data or "{}")
        match = re.search(r"/(grouping|seating)/export$", route.request.url)
        kind = match.group(1) if match else "unknown"
        captured["export"].append({**payload, "__kind": kind})
        route.fulfill(
            status=200,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"content-disposition": 'attachment; filename="pr-0303-proof.xlsx"'},
            body="PR-0303 export proof",
        )

    page.route(
        re.compile(
            r".*/api/v1/public/apps/classroom\.group-seating-studio/(grouping|seating)/share$"
        ),
        share_handler,
    )
    page.route(
        re.compile(
            r".*/api/v1/public/apps/classroom\.group-seating-studio/(grouping|seating)/export$"
        ),
        export_handler,
    )
    return captured


def _open_grouping_workspace_and_create_link(page: Page) -> None:
    """Create a grouping link from the workspace share surface."""

    focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()
    page.locator('[data-test="new-grouping-draft"]').click()
    _first_visible(
        page, '[data-test="grouping-layout-lane"], [data-test="phone-grouping-workspace"]'
    )

    trigger = page.locator('[data-test="grouping-share-trigger"]')
    if not _visible(trigger):
        page.locator('[data-test="grouping-actions-menu"]').click()
        trigger = page.locator('[data-test="grouping-overflow-share-trigger"]')
    expect(trigger).to_be_visible()
    trigger.click()

    panel = page.locator('[data-test="grouping-share-management"]')
    expect(panel).to_be_visible()
    panel.locator('[data-test="grouping-share-create"]').click()
    expect(page.locator('[data-test="planner-share-link-pr-0303-share-1"]')).to_be_visible(
        timeout=30_000
    )
    page.keyboard.press("Escape")


def _assert_snapshot_targets(
    payload: dict[str, Any], *, roster_name: str, template_name: str
) -> None:
    """Assert a captured public helper request uses the selected overview state."""

    if payload.get("__kind") != "grouping":
        raise AssertionError(f"Expected grouping helper request, got {payload.get('__kind')!r}.")
    snapshot = payload["snapshot"]
    draft = snapshot["grouping_draft"]
    if not draft:
        raise AssertionError("Expected captured request snapshot to include a grouping draft.")
    roster = next(
        entry for entry in snapshot["rosters"] if entry["local_id"] == draft["roster_local_id"]
    )
    template = next(
        entry for entry in snapshot["templates"] if entry["local_id"] == draft["template_local_id"]
    )
    if roster["name"] != roster_name:
        raise AssertionError(f"Expected selected roster {roster_name!r}, got {roster['name']!r}.")
    if template["name"] != template_name:
        raise AssertionError(
            f"Expected selected classroom {template_name!r}, got {template['name']!r}."
        )
    if snapshot["ui_state"]["current_screen"] != "class-workspace":
        raise AssertionError(
            f"Expected overview request to preserve class-workspace screen, got "
            f"{snapshot['ui_state']['current_screen']!r}."
        )
    if payload["expected_revision"] != draft["revision"]:
        raise AssertionError(
            "Expected helper request revision to match the prepared grouping draft."
        )


def _run(*, base_url: str) -> None:
    """Run the public guest overview distribution proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_suffix = str(int(time.time()))
    roster_name = f"PR0303 Klass {run_suffix}"
    template_name = f"PR0303 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        captured = _install_public_distribution_routes(page)

        page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _select_overview_assets(page, roster_name=roster_name, template_name=template_name)

        _open_grouping_workspace_and_create_link(page)
        focus_workspace_mode(page, label="Översikt")
        overview_panel = _first_visible(page, '[data-test="desktop-overview-share-export-panel"]')
        expect(overview_panel).to_be_visible()
        grouping_scope = overview_panel.locator('[data-test="planner-share-export-scope-grouping"]')
        expect(grouping_scope).to_be_enabled()
        grouping_scope.click(force=True)
        expect(grouping_scope).to_have_attribute("aria-pressed", "true")
        expect(
            overview_panel.locator('[data-test="planner-share-export-scope-meta"]')
        ).to_contain_text("Gruppindelning")
        expect(
            overview_panel.locator('[data-test="planner-share-link-pr-0303-share-1"]')
        ).to_be_visible()

        previous_share_count = len(captured["share"])
        overview_create = overview_panel.locator('[data-test="desktop-overview-share-create"]')
        expect(overview_create).to_have_count(1)
        overview_create.click()
        for _ in range(60):
            if len(captured["share"]) > previous_share_count:
                break
            page.wait_for_timeout(250)
        if len(captured["share"]) <= previous_share_count:
            error_locator = overview_panel.locator('[data-test="planner-share-error"]')
            error_text = error_locator.text_content(timeout=500) if error_locator.count() else None
            body_text = page.locator("body").inner_text(timeout=1000)
            raise AssertionError(
                "Overview share did not call helper endpoint; "
                f"error={error_text!r}; body_tail={body_text[-1000:]!r}."
            )
        expect(
            overview_panel.locator('[data-test="planner-share-link-pr-0303-share-2"]')
        ).to_be_visible(timeout=30_000)
        grouping_scope.click(force=True)
        expect(grouping_scope).to_have_attribute("aria-pressed", "true")
        expect(
            overview_panel.locator('[data-test="planner-share-export-scope-meta"]')
        ).to_contain_text("Gruppindelning")
        previous_export_count = len(captured["export"])
        overview_panel.locator('[data-test="desktop-overview-export-option-xlsx"]').click()
        for _ in range(60):
            if len(captured["export"]) > previous_export_count:
                break
            page.wait_for_timeout(250)
        if len(captured["export"]) <= previous_export_count:
            raise AssertionError("Overview export did not call any public helper endpoint.")

        if len(captured["share"]) < 2:
            raise AssertionError(
                f"Expected workspace and overview share calls, got {len(captured['share'])}."
            )
        if len(captured["export"]) < 1:
            raise AssertionError("Expected one overview export call.")
        _assert_snapshot_targets(
            captured["share"][1], roster_name=roster_name, template_name=template_name
        )
        _assert_snapshot_targets(
            captured["export"][0], roster_name=roster_name, template_name=template_name
        )

        page.screenshot(
            path=str(ARTIFACTS_DIR / "public-overview-distribution-proof.png"), full_page=True
        )
        context.close()
        browser.close()

    print(f"pr-0303-public-guest-overview-distribution: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the PR-0303 browser proof."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--start-vite", action="store_true")
    proof_args, config_argv = parser.parse_known_args(argv)
    config = get_config(config_argv)

    if proof_args.start_vite:
        with temporary_vite_server() as live_base:
            _run(base_url=live_base)
        return

    _run(base_url=config.base_url)


if __name__ == "__main__":  # pragma: no cover
    main()
