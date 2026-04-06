"""Live PR-0227 proof for the desktop grouping board height contract.

This script is a targeted browser proof for a bounded slice. It verifies the
desktop-only grouping-board contract against the running local SPA on both the
public guest route and the authenticated route.

Purpose:
    Prove that the empty/default 4-card desktop grouping board resolves to an
    exact `480px` two-row block at `1440x900`, that each card keeps a desktop
    `234px` minimum-height floor after assignment, and that populated cards can
    grow beyond that floor without internal scrolling.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic authenticated planner data through the real local API
    - writes screenshots under `.artifacts/pr-0227-group-board-height-check/`
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_template,
    focus_workspace_mode,
    open_class_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0227-group-board-height-check")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
DESKTOP_WIDTH = 1440
DESKTOP_HEIGHT = 900
EXPECTED_BOARD_HEIGHT = 480.0
EXPECTED_CARD_HEIGHT = 234.0
EXPECTED_ROW_GAP = 12.0
MEASUREMENT_TOLERANCE = 0.5


def _api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _session_cookie_domain(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.hostname:
        raise AssertionError("Expected base URL hostname for session-cookie setup.")
    return parsed.hostname


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


def _student_payload(count: int, *, prefix: str) -> list[dict[str, str]]:
    return [
        {
            "id": f"{prefix.lower()}-student-{index}",
            "display_name": f"{prefix} Elev {index:02d} med lang etikett for tillvaxtprov",
        }
        for index in range(1, count + 1)
    ]


def _create_auth_roster(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
    student_count: int,
) -> dict[str, object]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={"name": name, "students": _student_payload(student_count, prefix="Auth")},
    )


def _create_auth_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
) -> dict[str, object]:
    seats = [
        {"id": "seat-1", "x": 0, "y": 0, "zone": None},
        {"id": "seat-2", "x": 120, "y": 0, "zone": None},
    ]
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={"name": name, "grid_cols": 4, "grid_rows": 4, "seats": seats, "fixtures": []},
    )


def _create_auth_grouping_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
) -> None:
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
        payload={"roster_id": roster_id},
    )


def _prepare_authenticated_workspace(
    *, api_base_url: str, email: str, password: str
) -> tuple[str, str, str]:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    suffix = uuid4().hex[:6]
    roster = _create_auth_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0227 Auth Klass {suffix}",
        student_count=12,
    )
    template = _create_auth_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR0227 Auth Sal {suffix}",
    )
    _create_auth_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
    )
    session_cookie = session.cookies.get("skriptoteket_session")
    if not session_cookie:
        raise AssertionError("Missing skriptoteket_session cookie after API login.")
    return str(roster["name"]), str(template["name"]), session_cookie


def _create_public_roster(page: Page, *, roster_name: str, student_count: int) -> None:
    page.get_by_role("button", name="Ny klasslista").click()
    expect(page.get_by_role("heading", name="Ny klasslista")).to_be_visible(timeout=60_000)
    page.get_by_label("Klassens namn").fill(roster_name)
    page.get_by_label("Elever").fill(
        "\n".join(
            student["display_name"] for student in _student_payload(student_count, prefix="Publik")
        )
    )
    page.get_by_role("button", name="Skapa klasslista").click()
    expect(page.get_by_role("heading", name="Ny klasslista")).to_have_count(0)
    expect(page.locator('[data-test="overview-roster-select"]')).to_have_value(
        page.locator('[data-test="overview-roster-select"]').input_value()
    )


def _dismiss_upgrade_prompt_if_present(page: Page) -> None:
    prompt = page.get_by_role("button", name="Inte nu", exact=True)
    if prompt.count() > 0 and prompt.first.is_visible():
        prompt.first.click()


def _wait_for_grouping_surface(page: Page) -> None:
    focus_workspace_mode(page, label="Grupper")
    page.wait_for_timeout(250)
    new_draft_button = page.locator('[data-test="new-grouping-draft"]')
    if new_draft_button.count() > 0 and new_draft_button.first.is_visible():
        new_draft_button.first.click()
    expect(page.locator('[data-test="group-board"]')).to_be_visible(timeout=60_000)
    expect(page.locator('[data-test="group-card"]')).to_have_count(4, timeout=60_000)
    expect(page.locator('[data-test="grouping-student-pool"]')).to_be_visible(timeout=60_000)


def _measure_group_board(page: Page) -> dict[str, float | list[dict[str, float]]]:
    board = page.locator('[data-test="group-board"]').bounding_box()
    if board is None:
        raise AssertionError("Expected a visible grouping board with a concrete bounding box.")
    cards = page.locator('[data-test="group-card"]').evaluate_all(
        """(elements) => elements.map((element) => {
            const rect = element.getBoundingClientRect();
            return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                clientHeight: element.clientHeight,
                scrollHeight: element.scrollHeight,
                overflowY: getComputedStyle(element).overflowY,
            };
        })"""
    )
    if len(cards) != 4:
        raise AssertionError(f"Expected exactly four group cards, found {len(cards)}.")
    row_tops = sorted({round(card["y"], 2) for card in cards})
    if len(row_tops) != 2:
        raise AssertionError(f"Expected exactly two row tops for the 2x2 board, found {row_tops}.")
    first_row_top = row_tops[0]
    second_row_top = row_tops[1]
    first_row_card = next(card for card in cards if round(card["y"], 2) == first_row_top)
    row_gap = second_row_top - (first_row_top + first_row_card["height"])
    return {
        "board_height": board["height"],
        "row_gap": row_gap,
        "cards": cards,
    }


def _assert_empty_exact_board(page: Page, *, route_label: str, screenshot_name: str) -> None:
    measurements = _measure_group_board(page)
    board_height = float(measurements["board_height"])
    row_gap = float(measurements["row_gap"])
    cards = measurements["cards"]
    assert abs(board_height - EXPECTED_BOARD_HEIGHT) <= MEASUREMENT_TOLERANCE, (
        f"{route_label}: expected empty board height {EXPECTED_BOARD_HEIGHT}px, "
        f"got {board_height:.2f}px."
    )
    assert abs(row_gap - EXPECTED_ROW_GAP) <= MEASUREMENT_TOLERANCE, (
        f"{route_label}: expected row gap {EXPECTED_ROW_GAP}px, got {row_gap:.2f}px."
    )
    for index, card in enumerate(cards, start=1):
        assert abs(card["height"] - EXPECTED_CARD_HEIGHT) <= MEASUREMENT_TOLERANCE, (
            f"{route_label}: expected empty card {index} height {EXPECTED_CARD_HEIGHT}px, "
            f"got {card['height']:.2f}px."
        )
    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)


def _drag_student_into_first_group(page: Page) -> None:
    pool_student = page.locator('[data-test="grouping-student-pool"] button').first
    expect(pool_student).to_be_visible(timeout=60_000)
    before_pool_count = page.locator('[data-test="grouping-student-pool"] button').count()
    before_group_rows = page.locator('[data-test^="group-student-row-"]').count()
    target_group = page.locator('[data-test="group-card"]').first
    pool_student.drag_to(target_group)
    page.wait_for_timeout(200)
    after_pool_count = page.locator('[data-test="grouping-student-pool"] button').count()
    after_group_rows = page.locator('[data-test^="group-student-row-"]').count()
    if after_pool_count == before_pool_count:
        page.evaluate(
            """() => {
                const source = document.querySelector('[data-test="grouping-student-pool"] button');
                const target = document.querySelector('[data-test="group-card"]');
                if (!source || !target) {
                    throw new Error('Missing drag source or target for grouping fallback.');
                }
                const dataTransfer = new DataTransfer();
                source.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer }));
                target.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer }));
                target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer }));
            }"""
        )
        page.wait_for_timeout(200)
        after_pool_count = page.locator('[data-test="grouping-student-pool"] button').count()
        after_group_rows = page.locator('[data-test^="group-student-row-"]').count()
    expect(page.locator('[data-test^="group-student-row-"]').first).to_be_visible(timeout=60_000)
    assert after_pool_count == before_pool_count - 1, (
        f"Expected one student to leave the pool after drag, before={before_pool_count}, "
        f"after={after_pool_count}."
    )
    assert after_group_rows == before_group_rows + 1, (
        f"Expected one student row to appear in a group after drag, before={before_group_rows}, "
        f"after={after_group_rows}."
    )
    page.wait_for_timeout(200)


def _assert_card_floor_persists(page: Page, *, route_label: str) -> None:
    card_height = page.locator('[data-test="group-card"]').first.bounding_box()
    if card_height is None:
        raise AssertionError(
            f"{route_label}: missing first group-card bounding box after assignment."
        )
    assert card_height["height"] >= EXPECTED_CARD_HEIGHT - MEASUREMENT_TOLERANCE, (
        f"{route_label}: expected assigned card to keep at least {EXPECTED_CARD_HEIGHT}px, "
        f"got {card_height['height']:.2f}px."
    )


def _assert_card_can_grow_without_internal_scroll(page: Page, *, route_label: str) -> None:
    for _ in range(7):
        _drag_student_into_first_group(page)
    card_metrics = page.locator('[data-test="group-card"]').first.evaluate(
        """(element) => {
            const rect = element.getBoundingClientRect();
            return {
                height: rect.height,
                clientHeight: element.clientHeight,
                scrollHeight: element.scrollHeight,
                overflowY: getComputedStyle(element).overflowY,
            };
        }"""
    )
    assert card_metrics["height"] > EXPECTED_CARD_HEIGHT + 1.0, (
        f"{route_label}: expected populated card to grow beyond {EXPECTED_CARD_HEIGHT}px, "
        f"got {card_metrics['height']:.2f}px."
    )
    assert card_metrics["overflowY"] not in {"auto", "scroll"}, (
        f"{route_label}: expected no internal vertical scroller on populated card, "
        f"got overflow-y={card_metrics['overflowY']!r}."
    )
    assert card_metrics["scrollHeight"] <= card_metrics["clientHeight"] + 1.0, (
        f"{route_label}: expected populated card content to fit without internal scrolling, "
        f"clientHeight={card_metrics['clientHeight']:.2f}px, "
        f"scrollHeight={card_metrics['scrollHeight']:.2f}px."
    )


def _verify_public_route(page: Page, *, base_url: str) -> None:
    page.goto(f"{base_url}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
    page.set_viewport_size({"width": DESKTOP_WIDTH, "height": DESKTOP_HEIGHT})
    roster_name = f"PR0227 Public Klass {uuid4().hex[:6]}"
    template_name = f"PR0227 Public Sal {uuid4().hex[:6]}"
    _create_public_roster(page, roster_name=roster_name, student_count=12)
    create_template(page, template_name=template_name)
    _wait_for_grouping_surface(page)
    _assert_empty_exact_board(
        page,
        route_label="public route",
        screenshot_name="public-empty-board.png",
    )
    _drag_student_into_first_group(page)
    _assert_card_floor_persists(page, route_label="public route")
    _assert_card_can_grow_without_internal_scroll(page, route_label="public route")
    page.screenshot(path=str(ARTIFACTS_DIR / "public-populated-board.png"), full_page=True)


def _verify_authenticated_route(page: Page, *, base_url: str, roster_name: str) -> None:
    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    page.set_viewport_size({"width": DESKTOP_WIDTH, "height": DESKTOP_HEIGHT})
    _dismiss_upgrade_prompt_if_present(page)
    open_class_workspace(page, roster_name=roster_name)
    _wait_for_grouping_surface(page)
    _assert_empty_exact_board(
        page,
        route_label="authenticated route",
        screenshot_name="auth-empty-board.png",
    )
    _drag_student_into_first_group(page)
    _assert_card_floor_persists(page, route_label="authenticated route")
    _assert_card_can_grow_without_internal_scroll(page, route_label="authenticated route")
    page.screenshot(path=str(ARTIFACTS_DIR / "auth-populated-board.png"), full_page=True)


def main() -> None:
    config = get_config()
    api_base_url = _api_base_url(config.base_url)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    roster_name, _template_name, session_cookie = _prepare_authenticated_workspace(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        public_context = browser.new_context(
            viewport={"width": DESKTOP_WIDTH, "height": DESKTOP_HEIGHT}
        )
        public_page = public_context.new_page()
        _verify_public_route(public_page, base_url=config.base_url)
        public_context.close()

        auth_context = browser.new_context(
            viewport={"width": DESKTOP_WIDTH, "height": DESKTOP_HEIGHT}
        )
        auth_context.add_cookies(
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
        auth_page = auth_context.new_page()
        _verify_authenticated_route(auth_page, base_url=config.base_url, roster_name=roster_name)
        auth_context.close()
        browser.close()

    print(f"pr-0227-group-board-height-check: ok ({ARTIFACTS_DIR})")


if __name__ == "__main__":
    main()
