"""Live PR-0181 proof for teacher-facing Smart-settings copy in Klassrumskartan.

Purpose:
    Verify that the grouping and seating Smart-settings drawers use the shipped
    teacher-facing Swedish copy against the running dev stack.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic planner data through the real local API
    - writes screenshots under `.artifacts/pr-0181-smart-settings-copy-check/`
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

ARTIFACTS_DIR = Path(".artifacts/pr-0181-smart-settings-copy-check")
GROUPING_HISTORY_TEXT = "Minskar risken att samma elever hamnar i samma grupp igen."
GROUPING_CLASSROOM_TEXT = "Välj ett klassrum om Smart ska ta hänsyn till sittschemat."
GROUPING_SEATING_TEXT = (
    "Om det finns ett sittschema för det valda klassrummet kan Smart ta hänsyn till det. "
    "Finns inget sittschema påverkas inte grupperingen."
)
SEATING_HISTORY_TEXT = (
    "Om du tidigare har exporterat ett sittschema kan Smart använda det för att variera "
    "placeringen över tid."
)
RULES_TEXT = "Du lägger till och ändrar regler i arbetsytan Regler."


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
        {"id": f"student-{index}", "display_name": f"Elev {index:02d}"} for index in range(1, 9)
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
    seats = [
        {"id": "seat-1", "x": 0, "y": 0, "zone": None},
        {"id": "seat-2", "x": 120, "y": 0, "zone": None},
        {"id": "seat-3", "x": 0, "y": 120, "zone": None},
        {"id": "seat-4", "x": 120, "y": 120, "zone": None},
    ]
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={
            "name": name,
            "grid_cols": 4,
            "grid_rows": 4,
            "seats": seats,
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
) -> dict[str, object]:
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
) -> dict[str, object]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _prepare_workspace(api_base_url: str, email: str, password: str) -> str:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0181 Klass {suffix}",
    )
    template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0181 Sal {suffix}",
    )
    _create_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
        template_id=str(template["id"]),
    )
    _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
        template_id=str(template["id"]),
    )
    return str(roster["name"])


def _assert_grouping_copy(page: Page) -> None:
    focus_workspace_mode(page, label="Grupper")
    page.locator('[data-test="grouping-open-settings"]').click()
    drawer = page.locator('[data-test="grouping-settings-drawer"]')
    expect(drawer).to_be_visible(timeout=60000)
    expect(drawer).to_contain_text("Historik")
    expect(drawer).to_contain_text("Klassrum")
    expect(drawer).to_contain_text("Sittschemat")
    expect(drawer).to_contain_text(GROUPING_HISTORY_TEXT)
    expect(drawer).to_contain_text(GROUPING_CLASSROOM_TEXT)
    expect(drawer).to_contain_text(GROUPING_SEATING_TEXT)
    expect(drawer).to_contain_text(RULES_TEXT)
    drawer.screenshot(path=str(ARTIFACTS_DIR / "grouping-settings-copy.png"))
    page.get_by_label("Stäng Smart-inställningar").click()


def _assert_seating_copy(page: Page) -> None:
    focus_workspace_mode(page, label="Sittplatser")
    page.locator('[data-test="seating-open-settings"]').click()
    drawer = page.locator('[data-test="seating-settings-drawer"]')
    expect(drawer).to_be_visible(timeout=60000)
    expect(drawer).to_contain_text("Historik")
    expect(drawer).to_contain_text(SEATING_HISTORY_TEXT)
    expect(drawer).to_contain_text(RULES_TEXT)
    drawer.screenshot(path=str(ARTIFACTS_DIR / "seating-settings-copy.png"))
    page.get_by_label("Stäng Smart-inställningar").click()


def main() -> None:
    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    roster_name = _prepare_workspace(
        api_base_url=_api_base_url(config.base_url),
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
        _assert_grouping_copy(page)
        _assert_seating_copy(page)
        browser.close()

    print("pr-0181-smart-settings-copy-check: ok")


if __name__ == "__main__":
    main()
