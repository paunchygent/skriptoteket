"""Live PR-0177 proof for rule visibility and tool-feedback continuity.

Purpose:
    Verify the ST-29-09 UI continuity slice against the live local SPA by
    seeding one real planner workspace, then checking grouping markers, seating
    toolbar cleanup, and room-editor tool feedback.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic planner data through the real local API
    - writes screenshots under `.artifacts/pr-0177-rule-visibility-and-tool-feedback-check/`
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0177-rule-visibility-and-tool-feedback-check")


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
                {"id": "student-1", "display_name": "Ada Lovelace"},
                {"id": "student-2", "display_name": "Alan Turing"},
                {"id": "student-3", "display_name": "Grace Hopper"},
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
            "grid_cols": 5,
            "grid_rows": 3,
            "seats": [
                {"id": "seat-1", "x": 0, "y": 0, "zone": "front"},
                {"id": "seat-2", "x": 120, "y": 0, "zone": "front"},
            ],
            "fixtures": [
                {
                    "id": "teacher-desk-1",
                    "type": "teacher_desk",
                    "x": 84,
                    "y": 132,
                    "width": 168,
                    "height": 72,
                    "label": "Lärarbord",
                },
            ],
        },
    )


def _create_grouping_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
) -> dict:
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
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _patch_smart_rules(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
) -> dict:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/rosters/{roster_id}/smart-rules",
        payload={
            "expected_revision": 0,
            "seating_preferences": [{"student_id": "student-1", "near_teacher": True}],
            "relationship_rules": [
                {
                    "id": f"rule-{uuid4().hex[:8]}",
                    "kind": "keep_apart",
                    "student_ids": ["student-1", "student-3"],
                },
            ],
        },
    )


def _prepare_workspace(api_base_url: str, email: str, password: str) -> tuple[str, str]:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0177 Klass {suffix}",
    )
    template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0177 Sal {suffix}",
    )

    grouping_draft = _create_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
    )
    grouping_workspace = _api_get(
        session,
        api_base_url=api_base_url,
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{grouping_draft['id']}/workspace",
    )
    first_group_id = grouping_workspace["groups"][0]["id"]
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{grouping_draft['id']}",
        payload={
            "expected_revision": grouping_draft["revision"],
            "smart_enabled": True,
            "group_assignments": [{"student_id": "student-1", "group_id": first_group_id}],
        },
    )

    seating_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        template_id=template["id"],
    )
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{seating_draft['id']}",
        payload={
            "expected_revision": seating_draft["revision"],
            "smart_enabled": True,
            "seat_assignments": [
                {"student_id": "student-1", "seat_id": "seat-1"},
                {"student_id": "student-2", "seat_id": "seat-2"},
            ],
        },
    )
    _patch_smart_rules(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
    )
    return roster["name"], template["name"]


def _assert_grouping_markers(page: Page) -> None:
    focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-student-pool"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="student-pool-markers-student-3"]')).to_contain_text("Isär A")
    expect(page.locator('[data-test="group-student-markers-student-1"]')).to_contain_text(
        "Nära läraren"
    )
    expect(page.locator('[data-test="group-student-markers-student-1"]')).to_contain_text("Isär A")
    page.screenshot(path=str(ARTIFACTS_DIR / "grouping-rule-markers.png"), full_page=True)


def _assert_seating_cleanup(page: Page) -> None:
    focus_workspace_mode(page, label="Sittplatser")
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="seating-active-rule-count"]')).to_have_count(0)
    expect(page.locator('[data-test="student-pool-markers-student-3"]')).to_contain_text("Isär A")
    page.screenshot(path=str(ARTIFACTS_DIR / "seating-rule-visibility.png"), full_page=True)


def _assert_room_editor_feedback(page: Page) -> None:
    page.locator('[data-test="seating-actions-menu"]').click()
    page.locator('[data-test="edit-current-template"]').click()
    expect(page.get_by_role("heading", name="Redigera klassrum", exact=True)).to_be_visible(
        timeout=60000
    )
    expect(page.locator('[data-test="room-template-selected-tool-meta"]')).to_contain_text(
        "Placera plats"
    )
    page.locator('[data-test="room-template-tool-whiteboard"]').click()
    expect(page.locator('[data-test="room-template-selected-tool-meta"]')).to_contain_text(
        "Whiteboard"
    )
    expect(page.locator('[data-test="room-template-selected-tool-help"]')).to_contain_text("vägg")
    page.screenshot(path=str(ARTIFACTS_DIR / "room-editor-tool-feedback.png"), full_page=True)


def main() -> None:
    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    api_base_url = _api_base_url(config.base_url)
    roster_name, _template_name = _prepare_workspace(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        login_to_app(
            page,
            base_url=config.base_url,
            email=config.email,
            password=config.password,
        )
        open_class_workspace(page, roster_name=roster_name)
        _assert_grouping_markers(page)
        _assert_seating_cleanup(page)
        _assert_room_editor_feedback(page)
        browser.close()

    print("pr-0177-live-check: ok")


if __name__ == "__main__":
    main()
