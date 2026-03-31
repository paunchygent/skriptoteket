"""Live PR-0179 proof for sticky toolbar offset collapse in Klassrumskartan.

Purpose:
    Verify that the detached shared `Grupper` and `Sittplatser` toolbars pin
    flush to the viewport top while scrolling, but return to their in-layout
    resting position when the page scroll returns to the top.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic planner data through the real local API
    - writes screenshots under `.artifacts/pr-0179-sticky-toolbar-offset-check/`
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0179-sticky-toolbar-offset-check")
GROUPS_LABEL = "Grupper"
SEATS_LABEL = "Sittplatser"


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


def _session_cookie_domain(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.hostname:
        raise AssertionError("Expected base URL hostname for session-cookie setup.")
    return parsed.hostname


def _api_mutate(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
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
    name: str,
) -> dict[str, object]:
    students = [
        {"id": f"student-{index}", "display_name": f"Elev {index:02d}"} for index in range(1, 25)
    ]
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={"name": name, "students": students},
    )


def _create_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
) -> dict[str, object]:
    seats: list[dict[str, object]] = []
    seat_number = 1
    for row in range(8):
        for col in range(4):
            seats.append(
                {
                    "id": f"seat-{seat_number}",
                    "x": col * 120,
                    "y": row * 92,
                    "zone": "front" if row < 2 else None,
                }
            )
            seat_number += 1

    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={
            "name": name,
            "grid_cols": 6,
            "grid_rows": 10,
            "seats": seats,
            "fixtures": [
                {
                    "id": "teacher-desk-1",
                    "type": "teacher_desk",
                    "x": 120,
                    "y": 820,
                    "width": 168,
                    "height": 72,
                    "label": "Lärarbord",
                }
            ],
        },
    )


def _create_grouping_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
) -> dict[str, object]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
        payload={"roster_id": roster_id},
    )


def _create_seating_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> dict[str, object]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _prepare_workspace(api_base_url: str, email: str, password: str) -> tuple[str, str]:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0179 Klass {suffix}",
    )
    template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0179 Sal {suffix}",
    )
    _create_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
    )
    _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
        template_id=str(template["id"]),
    )
    session_cookie = session.cookies.get("skriptoteket_session")
    if not session_cookie:
        raise AssertionError("Missing skriptoteket_session cookie after API login.")
    return str(roster["name"]), session_cookie


def _document_metrics(page: Page) -> dict[str, float]:
    return page.evaluate(
        """() => ({
            scrollHeight: document.scrollingElement?.scrollHeight ?? 0,
            innerHeight: window.innerHeight,
            scrollY: window.scrollY,
        })"""
    )


def _toolbar_box(page: Page) -> dict[str, float]:
    toolbar = page.locator('[data-ui="planner-workspace-action-bar"]').first
    expect(toolbar).to_be_visible(timeout=60000)
    box = toolbar.bounding_box()
    if box is None:
        raise AssertionError("Expected a visible workspace toolbar with a concrete bounding box.")
    return box


def _scroll_to(page: Page, top: int) -> None:
    page.evaluate(f"window.scrollTo({{ top: {top}, behavior: 'instant' }})")
    page.wait_for_timeout(300)


def _ensure_page_scrollable(page: Page) -> None:
    metrics = _document_metrics(page)
    if metrics["scrollHeight"] > metrics["innerHeight"] + 48:
        return

    page.evaluate(
        """() => {
            let spacer = document.getElementById("pr0179-scroll-spacer");
            if (!spacer) {
                spacer = document.createElement("div");
                spacer.id = "pr0179-scroll-spacer";
                spacer.setAttribute("aria-hidden", "true");
                spacer.style.height = "140vh";
                spacer.style.pointerEvents = "none";
                spacer.style.opacity = "0";
                document.body.appendChild(spacer);
            }
        }"""
    )
    page.wait_for_timeout(150)

    metrics = _document_metrics(page)
    if metrics["scrollHeight"] <= metrics["innerHeight"] + 48:
        raise AssertionError("Page did not become scrollable for sticky-toolbar proof.")


def _assert_toolbar_flush_and_restoring(
    page: Page,
    *,
    workspace_label: str,
    screenshot_prefix: str,
) -> None:
    initial_box = _toolbar_box(page)
    _scroll_to(page, 800)
    stuck_box = _toolbar_box(page)
    assert stuck_box["y"] <= 1.5, (
        f"Expected the {workspace_label} toolbar to pin flush to the viewport top. "
        f"Got y={stuck_box['y']:.2f}px."
    )
    page.screenshot(path=str(ARTIFACTS_DIR / f"{screenshot_prefix}-stuck.png"), full_page=False)

    _scroll_to(page, 0)
    restored_box = _toolbar_box(page)
    assert abs(restored_box["y"] - initial_box["y"]) <= 2.0, (
        f"Expected the {workspace_label} toolbar to return to its initial in-layout position. "
        f"Initial y={initial_box['y']:.2f}px, restored y={restored_box['y']:.2f}px."
    )
    page.screenshot(path=str(ARTIFACTS_DIR / f"{screenshot_prefix}-start.png"), full_page=False)


def _assert_groups_toolbar(page: Page, *, viewport_label: str) -> None:
    focus_workspace_mode(page, label=GROUPS_LABEL)
    expect(page.locator('[data-test="grouping-history-cluster"]')).to_be_visible(timeout=60000)
    _ensure_page_scrollable(page)
    _assert_toolbar_flush_and_restoring(
        page,
        workspace_label=f"{GROUPS_LABEL} ({viewport_label})",
        screenshot_prefix=f"{viewport_label}-groups",
    )


def _assert_seats_toolbar(page: Page, *, viewport_label: str) -> None:
    focus_workspace_mode(page, label=SEATS_LABEL)
    expect(page.locator('[data-test="seating-history-cluster"]')).to_be_visible(timeout=60000)
    _ensure_page_scrollable(page)
    _assert_toolbar_flush_and_restoring(
        page,
        workspace_label=f"{SEATS_LABEL} ({viewport_label})",
        screenshot_prefix=f"{viewport_label}-seats",
    )


def main() -> None:
    config = get_config()
    api_base_url = _api_base_url(config.base_url)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    roster_name, session_cookie = _prepare_workspace(api_base_url, config.email, config.password)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context()
        context.add_cookies(
            [
                {
                    "name": "skriptoteket_session",
                    "value": session_cookie,
                    "domain": _session_cookie_domain(config.base_url),
                    "path": "/",
                    "httpOnly": True,
                }
            ]
        )
        page = context.new_page()
        page.goto(
            f"{config.base_url}/apps/classroom.group-seating-studio",
            wait_until="domcontentloaded",
        )
        open_class_workspace(page, roster_name=roster_name)

        for viewport_label, width, height in [
            ("laptop", 1366, 768),
            ("desktop", 1440, 900),
        ]:
            page.set_viewport_size({"width": width, "height": height})
            _scroll_to(page, 0)
            _assert_groups_toolbar(page, viewport_label=viewport_label)
            _assert_seats_toolbar(page, viewport_label=viewport_label)

        context.close()
        browser.close()

    print(f"pr-0179-sticky-toolbar-check: ok ({ARTIFACTS_DIR})")


if __name__ == "__main__":
    main()
