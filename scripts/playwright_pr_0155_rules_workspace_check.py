"""Live PR-0155 proof for the Klassrumskartan Regler workspace cut-over.

Purpose:
    Verify the shipped `Regler` workspace against the approved PR-0155 scope in
    the live local SPA.

Relationships:
    - reuses the shared Klassrumskartan Playwright helpers for login and
      overview/workspace navigation
    - seeds deterministic roster/template/draft data through the real local API
    - writes screenshots under `.artifacts/pr-0155-rules-workspace-check/`
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any
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

ARTIFACTS_DIR = Path(".artifacts/pr-0155-rules-workspace-check")
RULES_BOOTSTRAP_TRANSITION_LABEL = (
    "Förbereder Regler genom att starta ett sittschema i bakgrunden..."
)
RULES_BOOTSTRAP_NOTICE = "Regler använder ett sittschema i bakgrunden. Vi startade ett nytt sittschema för den här klassen."


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
        payload={
            "name": roster_name,
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
    template_name: str,
) -> dict[str, Any]:
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
                {"id": "seat-3", "x": 240, "y": 0, "zone": "front"},
            ],
            "fixtures": [
                {
                    "id": "teacher-desk-1",
                    "type": "teacher_desk",
                    "x": 48,
                    "y": 132,
                    "width": 168,
                    "height": 72,
                    "label": "Lärarbord",
                },
            ],
        },
    )


def _patch_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    expected_revision: int,
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}",
        payload={
            "expected_revision": expected_revision,
            "smart_enabled": True,
            "use_history": True,
            "seat_assignments": [
                {"student_id": "student-1", "seat_id": "seat-3"},
                {"student_id": "student-2", "seat_id": "seat-1"},
                {"student_id": "student-3", "seat_id": "seat-2"},
            ],
        },
    )


def _get_workspace_summary(
    session: requests.Session,
    *,
    api_base_url: str,
    roster_id: str,
) -> dict[str, Any]:
    response = session.get(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/rosters/{roster_id}/workspace-summary",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _patch_smart_rules(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    expected_revision: int,
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/rosters/{roster_id}/smart-rules",
        payload={
            "expected_revision": expected_revision,
            "seating_preferences": [{"student_id": "student-1", "near_teacher": True}],
            "relationship_rules": [
                {
                    "id": f"rule-{uuid4().hex[:8]}",
                    "kind": "keep_apart",
                    "student_ids": ["student-2", "student-3"],
                },
            ],
        },
    )


def _seat_button_texts(page: Page) -> list[str]:
    return page.locator(
        '[data-test="rules-map-canvas"] [data-test^="rules-seat-node-"] button'
    ).evaluate_all(
        """buttons => buttons.map(button => button.innerText.replace(/\\s+/g, " ").trim())"""
    )


def _select_overview_template(page: Page, *, template_name: str) -> None:
    template_select = page.locator('[data-test="overview-template-select"]')
    expect(template_select).to_be_visible(timeout=60000)
    option_rows = template_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and option["label"] == template_name
    )
    template_select.select_option(value=matching_option["value"])
    expect(template_select).to_have_value(matching_option["value"])


def _assert_rules_workspace(page: Page, *, template_name: str) -> None:
    expect(page.get_by_role("button", name="Regler", exact=True)).to_be_visible()
    expect(page.locator('[data-test="rules-map-canvas"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="rules-map-empty-state"]')).to_have_count(0)
    expect(page.get_by_role("button", name="Planeringskarta", exact=True)).to_have_attribute(
        "aria-pressed",
        "true",
    )
    expect(
        page.get_by_text(
            "Planeringskarta använder alfabetisk placering på klassrummets riktiga geometri.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.get_by_text(re.compile(re.escape(template_name)))).to_be_visible()

    seat_texts = _seat_button_texts(page)
    assert seat_texts[0].startswith("Ada Lovelace"), seat_texts
    assert seat_texts[1].startswith("Alan Turing"), seat_texts
    assert seat_texts[2].startswith("Grace Hopper"), seat_texts


def _assert_switch_to_seating_arrangement_preserves_selection(page: Page) -> None:
    page.locator('[data-test="rules-tool-keep_apart"]').click()
    page.get_by_role("button", name=re.compile(r"Alan Turing", re.IGNORECASE)).first.click()
    page.get_by_role("button", name=re.compile(r"Grace Hopper", re.IGNORECASE)).first.click()
    expect(page.get_by_text("2 valda", exact=False)).to_be_visible()
    expect(page.locator('[data-test="rules-commit-rule"]')).to_be_enabled()

    page.get_by_role("button", name="Sittschema", exact=True).click()

    expect(page.get_by_role("button", name="Sittschema", exact=True)).to_have_attribute(
        "aria-pressed",
        "true",
    )
    expect(page.get_by_text("2 valda", exact=False)).to_be_visible()
    expect(page.locator('[data-test="rules-commit-rule"]')).to_be_enabled()
    expect(page.locator('[data-test="rules-seat-order-seat-1"]')).to_be_visible()
    expect(page.locator('[data-test="rules-seat-order-seat-2"]')).to_be_visible()


def _assert_relationship_rule_edit_from_inspector(page: Page) -> None:
    page.locator('[data-test="rules-clear-selection"]').click()
    page.locator('[data-test="rules-edit-rule-0"]').click()
    expect(page.locator('[data-test="rules-commit-rule"]')).to_contain_text("Spara regel")
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).first.click()
    page.locator('[data-test="rules-commit-rule"]').click()
    rule_card_text = (
        page.locator('[data-test="rules-edit-rule-0"]')
        .locator("xpath=ancestor::div[contains(@class, 'border')]")
        .first.text_content()
        or ""
    )
    assert "Ada Lovelace" in rule_card_text, rule_card_text
    assert "Alan Turing" in rule_card_text, rule_card_text
    assert "Grace Hopper" in rule_card_text, rule_card_text


def _assert_near_teacher_edit_from_inspector(page: Page) -> None:
    page.locator('[data-test="rules-edit-near-teacher-0"]').click()
    page.locator('[data-test="rules-near-teacher-select-0"]').select_option("student-2")
    page.locator('[data-test="rules-save-near-teacher-0"]').click()


def _assert_compact_summary_workspace(
    page: Page,
    *,
    workspace_label: str,
    settings_test_id: str,
) -> None:
    focus_workspace_mode(page, label=workspace_label)
    expect(page.locator(f'[data-test="{settings_test_id}"]')).to_be_visible(timeout=60000)
    expect(page.get_by_text("Smarta regler", exact=True)).to_be_visible()
    expect(page.get_by_text("Närmare läraren: Alan Turing", exact=False)).to_be_visible()
    expect(page.locator('[data-test="rules-commit-rule"]')).to_have_count(0)
    expect(page.locator('[data-test="rules-edit-rule-0"]')).to_have_count(0)
    expect(page.get_by_text("Pågående regel", exact=True)).to_have_count(0)


def main() -> None:
    """Run the live Regler cut-over proof against the canonical local SPA."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _api_base_url(base_url)
    suffix = uuid4().hex[:6]
    roster_name = f"PR0155 Klass {suffix}"
    template_name = f"PR0155 Sal {suffix}"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    session, csrf_token = _login_api(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )
    roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_name=roster_name,
    )
    template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        template_name=template_name,
    )
    _patch_smart_rules(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        expected_revision=0,
    )

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()
        delayed_resolve_requests = {"count": 0}

        def _delay_first_rules_bootstrap(route: Any) -> None:
            delayed_resolve_requests["count"] += 1
            if delayed_resolve_requests["count"] == 1:
                time.sleep(0.35)
            response = route.fetch()
            route.fulfill(response=response)

        page.route(
            "**/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
            _delay_first_rules_bootstrap,
        )

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        open_class_workspace(page, roster_name=roster_name)
        _select_overview_template(page, template_name=template_name)

        focus_workspace_mode(page, label="Regler")
        expect(page.get_by_text(RULES_BOOTSTRAP_TRANSITION_LABEL, exact=True)).to_be_visible()
        expect(page.locator('[data-test="planner-workspace-notice"]')).to_contain_text(
            RULES_BOOTSTRAP_NOTICE,
            timeout=60000,
        )
        _assert_rules_workspace(page, template_name=template_name)
        page.screenshot(
            path=str(ARTIFACTS_DIR / "rules-bootstrap-planeringskarta.png"), full_page=True
        )

        workspace_summary = _get_workspace_summary(
            session,
            api_base_url=api_base_url,
            roster_id=roster["id"],
        )
        active_seating_draft = workspace_summary.get("active_seating_draft")
        assert active_seating_draft is not None, workspace_summary
        assert active_seating_draft["template_id"] == template["id"], active_seating_draft
        assert delayed_resolve_requests["count"] >= 1, delayed_resolve_requests

        _patch_draft(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            draft_id=active_seating_draft["id"],
            expected_revision=active_seating_draft["revision"],
        )

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        open_class_workspace(page, roster_name=roster_name)
        focus_workspace_mode(page, label="Regler")
        _assert_rules_workspace(page, template_name=template_name)
        page.screenshot(path=str(ARTIFACTS_DIR / "rules-planeringskarta.png"), full_page=True)

        _assert_switch_to_seating_arrangement_preserves_selection(page)
        _assert_relationship_rule_edit_from_inspector(page)
        _assert_near_teacher_edit_from_inspector(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "rules-sittschema.png"), full_page=True)

        _assert_compact_summary_workspace(
            page,
            workspace_label="Sittplatser",
            settings_test_id="seating-open-rules",
        )
        page.screenshot(path=str(ARTIFACTS_DIR / "seating-summary.png"), full_page=True)

        _assert_compact_summary_workspace(
            page,
            workspace_label="Grupper",
            settings_test_id="grouping-open-rules",
        )
        page.screenshot(path=str(ARTIFACTS_DIR / "grouping-summary.png"), full_page=True)

        context.close()
        browser.close()

    print(f"playwright-pr0155: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
