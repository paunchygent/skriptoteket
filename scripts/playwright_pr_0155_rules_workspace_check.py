"""Live PR-0155 proof for the Klassrumskartan Regler workspace cut-over.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


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
from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config

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
            "grid_cols": 13,
            "grid_rows": 8,
            "seats": [
                {"id": "seat-1", "x": 96, "y": 480, "zone": "front"},
                {"id": "seat-2", "x": 576, "y": 480, "zone": "front"},
                {"id": "seat-3", "x": 960, "y": 480, "zone": "front"},
            ],
            "fixtures": [
                {
                    "id": "teacher-desk-1",
                    "type": "teacher_desk",
                    "x": 96,
                    "y": 192,
                    "width": 168,
                    "height": 72,
                    "label": "Lärarbord",
                },
                {
                    "id": "whiteboard-1",
                    "type": "whiteboard",
                    "x": 96,
                    "y": 0,
                    "width": 1056,
                    "height": 72,
                    "label": "Whiteboard",
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


def _planning_student_button_texts(page: Page) -> list[str]:
    return page.locator('[data-test="rules-map-unplaced-grid"] button').evaluate_all(
        """buttons => buttons.map(button => button.innerText.replace(/\\s+/g, " ").trim())"""
    )


def _bounding_box(locator: Locator) -> dict[str, float]:
    box = locator.bounding_box()
    if box is None:
        raise AssertionError("Expected a visible element with a concrete bounding box.")
    return box


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


def _assert_rules_workspace(page: Page, *, roster_name: str) -> None:
    expect(
        page.locator('[data-test="rules-map-toolbar"] [data-test="rules-map-view-switch"]')
    ).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="rules-summary-panel"]')).to_be_visible(timeout=60000)
    expect(
        page.locator('[data-test="rules-tool-rail"] [data-test="rules-map-view-switch"]')
    ).to_have_count(0)
    expect(page.locator('[data-test="rules-map-panel"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="rules-map-canvas"]')).to_have_count(0)
    expect(page.locator('[data-test="rules-map-empty-state"]')).to_have_count(0)
    expect(page.locator('[data-test="rules-map-unplaced"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="rules-map-surface-heading"]')).to_have_text(roster_name)
    expect(page.locator('[data-test="rules-map-unplaced-count"]')).to_contain_text("3 elever")
    expect(page.locator('[data-test="rules-map-view-planning"]')).to_contain_text("Planeringsvy")
    expect(page.locator('[data-test="rules-map-view-seating"]')).to_contain_text("Klassrumsvy")
    expect(
        page.locator('[data-test="rules-tool-near_teacher"]').get_by_text("Nära läraren")
    ).to_be_visible()
    expect(
        page.locator('[data-test="rules-active-cards"]').get_by_text("Nära läraren")
    ).to_be_visible()
    expect(page.get_by_text("Närmare läraren", exact=True)).to_have_count(0)
    expect(page.get_by_text(re.compile(r"\\btotalt\\b", re.IGNORECASE))).to_have_count(0)
    expect(
        page.locator('[data-test="rules-summary-panel"] [data-test="rules-commit-rule"]')
    ).to_have_count(0)
    expect(
        page.locator('[data-test="rules-map-toolbar"] [data-test="rules-map-view-planning"]')
    ).to_have_attribute(
        "aria-checked",
        "true",
    )
    expect(page.locator('[data-test="rules-zoom-out"]')).to_be_disabled()
    expect(page.locator('[data-test="rules-zoom-in"]')).to_be_disabled()
    expect(page.locator('[data-test="rules-zoom-fit"]')).to_be_disabled()

    summary_panel_box = _bounding_box(page.locator('[data-test="rules-summary-panel"]'))
    tool_rail_box = _bounding_box(page.locator('[data-test="rules-tool-rail"]'))
    map_panel_box = _bounding_box(page.locator('[data-test="rules-map-panel"]'))
    tool_button_box = _bounding_box(page.locator('[data-test="rules-tool-near_teacher"]'))
    rule_card_box = _bounding_box(page.locator('[data-test="rules-active-card"]').first)

    assert summary_panel_box["y"] < map_panel_box["y"], (
        summary_panel_box,
        map_panel_box,
    )
    assert map_panel_box["width"] > tool_rail_box["width"] * 4, (
        map_panel_box,
        tool_rail_box,
    )
    assert tool_button_box["height"] <= 40.5, tool_button_box
    assert rule_card_box["width"] < summary_panel_box["width"] * 0.45, (
        rule_card_box,
        summary_panel_box,
    )

    planning_texts = _planning_student_button_texts(page)
    assert planning_texts[0].startswith("Ada Lovelace"), planning_texts
    assert planning_texts[1].startswith("Alan Turing"), planning_texts
    assert planning_texts[2].startswith("Grace Hopper"), planning_texts


def _assert_switch_to_seating_arrangement_preserves_selection(page: Page) -> None:
    page.locator('[data-test="rules-tool-keep_apart"]').click()
    page.get_by_role("button", name=re.compile(r"Alan Turing", re.IGNORECASE)).first.click()
    page.get_by_role("button", name=re.compile(r"Grace Hopper", re.IGNORECASE)).first.click()
    expect(page.locator(".planner-tool-rail-meta")).to_contain_text("2 valda")
    expect(page.locator('[data-test="rules-commit-rule"]')).to_be_enabled()

    page.locator('[data-test="rules-map-toolbar"] [data-test="rules-map-view-seating"]').click()

    expect(
        page.locator('[data-test="rules-map-toolbar"] [data-test="rules-map-view-seating"]')
    ).to_have_attribute(
        "aria-checked",
        "true",
    )
    expect(page.locator(".planner-tool-rail-meta")).to_contain_text("2 valda")
    expect(page.locator('[data-test="rules-commit-rule"]')).to_be_enabled()
    expect(page.locator('[data-test="rules-seat-order-seat-1"]')).to_be_visible()
    expect(page.locator('[data-test="rules-seat-order-seat-2"]')).to_be_visible()


def _assert_seating_zoom_and_scroll_behavior(page: Page) -> None:
    zoom_percent = page.locator('[data-test="rules-zoom-percent"]')
    zoom_out = page.locator('[data-test="rules-zoom-out"]')
    zoom_in = page.locator('[data-test="rules-zoom-in"]')
    zoom_fit = page.locator('[data-test="rules-zoom-fit"]')
    seating_canvas = page.locator('[data-test="rules-map-canvas"]')

    expect(zoom_out).to_be_enabled()
    expect(zoom_in).to_be_enabled()
    expect(zoom_fit).to_be_enabled()

    fit_percent_text = (zoom_percent.text_content() or "").strip().rstrip("%")
    fit_percent = int(fit_percent_text)
    assert fit_percent != 100, fit_percent

    zoom_out.click()
    zoomed_out_percent = int(((zoom_percent.text_content() or "").strip().rstrip("%")))
    assert zoomed_out_percent < fit_percent, (zoomed_out_percent, fit_percent)

    zoom_fit.click()
    expect(zoom_percent).to_have_text(f"{fit_percent}%")

    for _ in range(4):
        zoom_in.click()

    overflow = seating_canvas.evaluate(
        """element => ({
            scrollWidth: element.scrollWidth,
            clientWidth: element.clientWidth,
            scrollHeight: element.scrollHeight,
            clientHeight: element.clientHeight,
        })"""
    )
    assert overflow["scrollWidth"] > overflow["clientWidth"], overflow

    scrolled = seating_canvas.evaluate(
        """element => {
            element.scrollLeft = element.scrollWidth;
            element.scrollTop = element.scrollHeight;
            return {
                scrollLeft: element.scrollLeft,
                scrollTop: element.scrollTop,
            };
        }"""
    )
    assert scrolled["scrollLeft"] > 0, scrolled
    if overflow["scrollHeight"] > overflow["clientHeight"]:
        assert scrolled["scrollTop"] > 0, scrolled


def _assert_relationship_rule_edit_from_inspector(page: Page) -> None:
    page.locator('[data-test="rules-clear-selection"]').click()
    page.locator('[data-test="rules-edit-rule-0"]').click()
    expect(page.locator('[data-test="rules-commit-rule"]')).to_contain_text("Spara regel")
    page.locator('[data-test="rules-map-panel"]').get_by_role(
        "button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)
    ).first.click()
    page.locator('[data-test="rules-commit-rule"]').click()
    rule_card_text = (
        page.locator('[data-test="rules-edit-rule-0"]')
        .locator("xpath=ancestor::*[@data-test='rules-active-card'][1]")
        .first.text_content()
        or ""
    )
    assert "Ada Lovelace" in rule_card_text, rule_card_text
    assert "Alan Turing" in rule_card_text, rule_card_text
    assert "Grace Hopper" in rule_card_text, rule_card_text


def _assert_near_teacher_edit_from_inspector(page: Page) -> None:
    page.locator('[data-test="rules-edit-near-teacher-0"]').click()
    expect(page.locator('[data-test="rules-tool-near_teacher"]')).to_have_class(
        re.compile(r"planner-choice-button-active")
    )
    expect(page.locator('[data-test="rules-commit-rule"]')).to_contain_text("Spara regel")
    expect(page.locator('[data-test="rules-pending-student-chip"]')).to_have_count(1)
    expect(page.locator(".planner-tool-rail-meta")).to_contain_text("1 vald")

    page.locator('[data-test="rules-map-panel"]').get_by_role(
        "button", name=re.compile(r"Alan Turing", re.IGNORECASE)
    ).first.click()

    expect(page.locator('[data-test="rules-pending-student-chip"]')).to_have_count(2)
    expect(page.locator(".planner-tool-rail-meta")).to_contain_text("2 valda")

    page.locator('[data-test="rules-commit-rule"]').click()

    near_teacher_card = (
        page.locator('[data-test="rules-edit-near-teacher-0"]')
        .locator("xpath=ancestor::*[@data-test='rules-active-card'][1]")
        .first
    )
    expect(near_teacher_card).to_contain_text("Ada Lovelace")
    expect(near_teacher_card).to_contain_text("Alan Turing")


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
        browser = launch_chromium(playwright)
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
        if page.get_by_text(RULES_BOOTSTRAP_TRANSITION_LABEL, exact=True).count():
            expect(page.get_by_text(RULES_BOOTSTRAP_TRANSITION_LABEL, exact=True)).to_be_visible()
        if page.locator('[data-test="planner-workspace-notice"]').count():
            expect(page.locator('[data-test="planner-workspace-notice"]')).to_contain_text(
                RULES_BOOTSTRAP_NOTICE,
                timeout=60000,
            )
        _assert_rules_workspace(page, roster_name=roster_name)
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
        _assert_rules_workspace(page, roster_name=roster_name)
        page.screenshot(path=str(ARTIFACTS_DIR / "rules-planeringskarta.png"), full_page=True)

        _assert_switch_to_seating_arrangement_preserves_selection(page)
        _assert_seating_zoom_and_scroll_behavior(page)
        _assert_relationship_rule_edit_from_inspector(page)
        _assert_near_teacher_edit_from_inspector(page)
        page.screenshot(path=str(ARTIFACTS_DIR / "rules-sittschema.png"), full_page=True)

        context.close()
        browser.close()

    print(f"playwright-pr0155: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
