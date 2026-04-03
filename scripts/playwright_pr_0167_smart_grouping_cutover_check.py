"""Live PR-0167 proof for grouping/seating toolbar cutover and smart grouping.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


Purpose:
    Verify the settled PR-0167 toolbar contract against the live Docker-backed
    SPA by seeding one real planner workspace, then checking the grouping and
    seating toolbars, both Smart settings drawers, the backend-owned no-history
    block, and one successful smart grouping rerun with seating influence.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic planner data through the real local API
    - writes screenshots under `.artifacts/pr-0167-smart-grouping-cutover-check/`
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0167-toolbar-check")
NO_HISTORY_MESSAGE = (
    "För att använda historik behöver du först exportera en gruppindelning för den här klassen."
)
SUCCESS_MESSAGE = "Smart gruppindelning klar med stöd från klassens sittning."


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
    payload: dict | None = None,
) -> dict:
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


def _api_get(session: requests.Session, *, api_base_url: str, path: str) -> dict:
    response = session.get(f"{api_base_url}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def _create_roster(
    session: requests.Session, *, api_base_url: str, csrf_token: str, name: str
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={
            "name": name,
            "students": [
                {"id": "ada", "display_name": "Ada Lovelace"},
                {"id": "alan", "display_name": "Alan Turing"},
                {"id": "bea", "display_name": "Bea Example"},
                {"id": "cai", "display_name": "Cai Example"},
            ],
        },
    )


def _create_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={
            "name": name,
            "grid_cols": 4,
            "grid_rows": 3,
            "seats": [
                {"id": "seat-1", "x": 0, "y": 0, "zone": "front-left"},
                {"id": "seat-2", "x": 120, "y": 0, "zone": "front-right"},
                {"id": "seat-3", "x": 0, "y": 120, "zone": "back-left"},
                {"id": "seat-4", "x": 120, "y": 120, "zone": "back-right"},
            ],
            "fixtures": [],
        },
    )


def _create_grouping_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _create_seating_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _patch_grouping_flags(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    revision: int,
) -> None:
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}",
        payload={
            "expected_revision": revision,
            "smart_enabled": True,
            "use_history": True,
            "grouping_seating_distance_enabled": True,
        },
    )


def _patch_seating_assignments(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    revision: int,
) -> None:
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}",
        payload={
            "expected_revision": revision,
            "smart_enabled": True,
            "seat_assignments": [
                {"student_id": "ada", "seat_id": "seat-1"},
                {"student_id": "alan", "seat_id": "seat-2"},
                {"student_id": "bea", "seat_id": "seat-3"},
                {"student_id": "cai", "seat_id": "seat-4"},
            ],
        },
    )


def _prepare_workspace(api_base_url: str, email: str, password: str) -> str:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0167 Klass {suffix}",
    )
    template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0167 Sal {suffix}",
    )
    grouping_draft = _create_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        template_id=template["id"],
    )
    _patch_grouping_flags(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=grouping_draft["id"],
        revision=grouping_draft["revision"],
    )
    seating_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        template_id=template["id"],
    )
    _patch_seating_assignments(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=seating_draft["id"],
        revision=seating_draft["revision"],
    )
    return roster["name"]


def _expect_toast_message(page: Page, *, message: str) -> None:
    expect(page.locator(".toast-message").filter(has_text=message).first).to_be_visible(
        timeout=60000
    )


def _assert_grouping_cutover(page: Page) -> None:
    expect(page.locator('[data-test="grouping-roster-select"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="grouping-template-select"]')).to_have_count(0)
    expect(page.locator('[data-test="grouping-active-rule-count"]')).to_have_count(0)
    expect(page.locator('[data-test="grouping-use-history-toggle"]')).to_have_count(0)
    expect(page.locator('[data-test="grouping-open-settings"]')).to_have_attribute(
        "aria-label", "Smart-inställningar"
    )

    page.screenshot(path=str(ARTIFACTS_DIR / "grouping-toolbar-live.png"), full_page=True)
    page.locator('[data-test="grouping-open-settings"]').click()
    expect(page.locator('[data-test="grouping-settings-drawer"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="grouping-settings-drawer"]')).to_contain_text("Historik")
    expect(page.locator('[data-test="grouping-settings-drawer"]')).to_contain_text("Klassrum")
    expect(page.locator('[data-test="grouping-settings-drawer"]')).to_contain_text("Sittning")
    page.screenshot(path=str(ARTIFACTS_DIR / "grouping-settings-drawer-live.png"), full_page=True)
    page.mouse.click(320, 220)

    page.locator('[data-test="randomize-groups"]').click()
    _expect_toast_message(page, message=NO_HISTORY_MESSAGE)
    page.screenshot(path=str(ARTIFACTS_DIR / "grouping-no-history-block.png"), full_page=True)

    page.locator('[data-test="grouping-open-settings"]').click()
    page.locator('[data-test="grouping-settings-history-toggle"]').click()
    page.mouse.click(320, 220)
    page.locator('[data-test="randomize-groups"]').click()
    _expect_toast_message(page, message=SUCCESS_MESSAGE)
    page.screenshot(path=str(ARTIFACTS_DIR / "grouping-smart-success.png"), full_page=True)


def _assert_seating_cutover(page: Page) -> None:
    expect(page.locator('[data-test="seating-template-select"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="seating-use-history-toggle"]')).to_have_count(0)
    expect(page.locator('[data-test="seating-open-rules"]')).to_have_count(0)
    expect(page.locator('[data-test="seating-open-settings"]')).to_have_attribute(
        "aria-label", "Smart-inställningar"
    )
    toolbar_metrics = page.locator('[data-ui="planner-workspace-action-bar"]').evaluate(
        """(element) => ({
            overflowX: window.getComputedStyle(element).overflowX,
            overflowY: window.getComputedStyle(element).overflowY,
            scrollWidth: element.scrollWidth,
            clientWidth: element.clientWidth,
        })"""
    )
    assert toolbar_metrics["overflowX"] == "visible"
    assert toolbar_metrics["scrollWidth"] <= toolbar_metrics["clientWidth"] + 1
    page.screenshot(path=str(ARTIFACTS_DIR / "seating-toolbar-live.png"), full_page=True)

    page.locator('[data-test="seating-open-settings"]').click()
    expect(page.locator('[data-test="seating-settings-drawer"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="seating-settings-drawer"]')).to_contain_text("Historik")
    expect(page.locator('[data-test="seating-settings-drawer"]')).to_contain_text("Regler")
    page.screenshot(path=str(ARTIFACTS_DIR / "seating-settings-drawer-live.png"), full_page=True)
    page.mouse.click(320, 220)

    page.locator('[data-test="seating-actions-menu"]').click()
    expect(page.locator('[data-test="seating-history"]')).to_be_visible(timeout=60000)
    page.screenshot(path=str(ARTIFACTS_DIR / "seating-overflow-live.png"), full_page=True)


def main() -> None:
    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    api_base_url = _api_base_url(config.base_url)
    roster_name = _prepare_workspace(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        login_to_app(
            page,
            base_url=config.base_url,
            email=config.email,
            password=config.password,
        )
        open_class_workspace(page, roster_name=roster_name)
        focus_workspace_mode(page, label="Grupper")
        _assert_grouping_cutover(page)
        focus_workspace_mode(page, label="Sittplatser")
        _assert_seating_cutover(page)
        browser.close()

    print("pr-0167-live-check: ok")


if __name__ == "__main__":
    main()
