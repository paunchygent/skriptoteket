"""Live PR-0227 / PR-0228 planner shell proof for real grouping and seating surfaces.

This script is a targeted browser proof for a bounded slice. It verifies the
desktop-only grouping-board and planner-shell contracts against the running
local SPA on the authenticated route using the real roster and classroom data.

Purpose:
    Prove that the empty/default 4-card desktop grouping board resolves to an
    exact `480px` two-row block at `1440x900`, that each card keeps a desktop
    `234px` minimum-height floor after assignment, that populated cards can
    grow beyond that floor without internal scrolling, and that the desktop
    planner shell keeps the workspace body visible across the real `1279px`,
    `1366x768`, and `1440x900` proof widths while the page scroll can move past
    the large top panel, the toolbar becomes the sticky working band, and the
    `480px` student-pool rail remains present with its own list-body overflow
    for the real `SA24D` roster and `G20` classroom.

Relationships:
    - reuses the shared Klassrumskartan Playwright login/workspace helpers
    - seeds deterministic authenticated planner data through the real local API
    - writes screenshots under `.artifacts/pr-0227-group-board-height-check/`
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    focus_workspace_mode,
    open_class_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0227-group-board-height-check")
DESKTOP_WIDTH = 1440
DESKTOP_HEIGHT = 900
LAPTOP_WIDTH = 1366
LAPTOP_HEIGHT = 768
EXPECTED_BOARD_HEIGHT = 480.0
EXPECTED_CARD_HEIGHT = 234.0
EXPECTED_ROW_GAP = 12.0
MEASUREMENT_TOLERANCE = 0.5
STICKY_TOLERANCE = 2.0
INTERMEDIATE_WIDTH = 1279
INTERMEDIATE_HEIGHT = 900
GROUPING_OVERFLOW_COUNT = 8
AUTH_ROSTER_NAME = "SA24D"
AUTH_TEMPLATE_NAME = "G20"


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


def _list_auth_rosters(
    session: requests.Session,
    *,
    api_base_url: str,
) -> list[dict[str, object]]:
    response = session.get(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/rosters",
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list):
        return payload
    return list(payload.get("rosters", []))


def _list_auth_templates(
    session: requests.Session,
    *,
    api_base_url: str,
) -> list[dict[str, object]]:
    response = session.get(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/templates",
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list):
        return payload
    return list(payload.get("templates", []))


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


def _create_auth_seating_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> None:
    _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _prepare_authenticated_workspace(
    *, api_base_url: str, email: str, password: str
) -> tuple[str, str, str]:
    session, csrf_token = _login_api(api_base_url=api_base_url, email=email, password=password)
    roster = next(
        (
            entry
            for entry in _list_auth_rosters(session, api_base_url=api_base_url)
            if str(entry.get("name")) == AUTH_ROSTER_NAME
        ),
        None,
    )
    if roster is None:
        raise AssertionError(
            f"Expected authenticated roster {AUTH_ROSTER_NAME!r} to exist for live verification."
        )
    template = next(
        (
            entry
            for entry in _list_auth_templates(session, api_base_url=api_base_url)
            if str(entry.get("name")) == AUTH_TEMPLATE_NAME
        ),
        None,
    )
    if template is None:
        raise AssertionError(
            f"Expected authenticated classroom {AUTH_TEMPLATE_NAME!r} to exist for live verification."
        )
    _create_auth_grouping_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
    )
    _create_auth_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=str(roster["id"]),
        template_id=str(template["id"]),
    )
    session_cookie = session.cookies.get("skriptoteket_session")
    if not session_cookie:
        raise AssertionError("Missing skriptoteket_session cookie after API login.")
    return str(roster["name"]), str(template["name"]), session_cookie


def _set_viewport(page: Page, *, width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(250)


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


def _wait_for_seating_surface(page: Page) -> None:
    focus_workspace_mode(page, label="Sittplatser")
    page.wait_for_timeout(250)
    new_draft_button = page.locator('[data-test="new-seating-draft"]')
    if new_draft_button.count() > 0 and new_draft_button.first.is_visible():
        new_draft_button.first.click()
    expect(page.locator('[data-test="seating-student-pool"]')).to_be_visible(timeout=60_000)
    expect(page.locator('[data-test="room-canvas-viewport"]')).to_be_visible(timeout=60_000)


def _assert_workspace_body_visible_below_toolbar(
    page: Page,
    *,
    view: str,
    body_test_ids: list[str],
    route_label: str,
    width_label: str,
    screenshot_name: str,
) -> None:
    toolbar = page.locator(f'[data-ui="planner-workspace-toolbar-shell"][data-view="{view}"]')
    expect(toolbar).to_be_visible(timeout=60_000)
    toolbar_box = toolbar.bounding_box()
    if toolbar_box is None:
        raise AssertionError(f"{route_label} {width_label}: missing toolbar bounding box.")
    for test_id in body_test_ids:
        locator = page.locator(f'[data-test="{test_id}"]')
        expect(locator).to_be_visible(timeout=60_000)
        box = locator.bounding_box()
        if box is None:
            raise AssertionError(
                f"{route_label} {width_label}: missing body bounding box for {test_id}."
            )
        assert box["height"] > 40, (
            f"{route_label} {width_label}: expected {test_id} to render a real body surface, "
            f"got height={box['height']:.2f}px."
        )
        assert box["y"] >= toolbar_box["y"] + toolbar_box["height"] - STICKY_TOLERANCE, (
            f"{route_label} {width_label}: expected {test_id} to remain visible below the toolbar, "
            f"toolbarBottom={(toolbar_box['y'] + toolbar_box['height']):.2f}px "
            f"bodyTop={box['y']:.2f}px."
        )
    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)


def _set_group_count(page: Page, *, target_count: int) -> None:
    count_value = page.locator('[data-test="group-count-value"]')
    expect(count_value).to_be_visible(timeout=60_000)
    while int(count_value.inner_text()) < target_count:
        page.locator('[data-test="increment-group-count"]').click()
        page.wait_for_timeout(100)
    expect(page.locator('[data-test="group-card"]')).to_have_count(target_count, timeout=60_000)


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


def _pane_shell_locator(page: Page, *, view: str):
    return page.locator(f'[data-ui="planner-workspace-pane-shell"][data-view="{view}"]')


def _resolve_scroll_context(page: Page, *, view: str) -> dict[str, float | str]:
    contexts = page.evaluate(
        """(view) => {
            const result = [];
            const paneShell = document.querySelector(
                `[data-ui="planner-workspace-pane-shell"][data-view="${view}"]`
            );
            if (paneShell) {
                result.push({
                    kind: "pane-shell",
                    scrollHeight: paneShell.scrollHeight,
                    clientHeight: paneShell.clientHeight,
                    scrollTop: paneShell.scrollTop,
                });
            }
            const authMain = document.querySelector("main.auth-main-content");
            if (authMain) {
                result.push({
                    kind: "auth-main",
                    scrollHeight: authMain.scrollHeight,
                    clientHeight: authMain.clientHeight,
                    scrollTop: authMain.scrollTop,
                });
            }
            const documentScroller = document.scrollingElement;
            if (documentScroller) {
                result.push({
                    kind: "document",
                    scrollHeight: documentScroller.scrollHeight,
                    clientHeight: window.innerHeight,
                    scrollTop: documentScroller.scrollTop,
                });
            }
            return result;
        }""",
        view,
    )
    for kind in ("pane-shell", "auth-main", "document"):
        match = next((entry for entry in contexts if entry["kind"] == kind), None)
        if match and (match["scrollHeight"] - match["clientHeight"]) > 64:
            return match
    raise AssertionError(
        f"Expected one visible scroll context for {view} sticky proof, found: {contexts!r}."
    )


def _scroll_context_to(page: Page, *, view: str, kind: str, target_scroll_top: float) -> float:
    return float(
        page.evaluate(
            """({ view, kind, targetScrollTop }) => {
                const resolveElement = () => {
                    if (kind === "pane-shell") {
                        return document.querySelector(
                            `[data-ui="planner-workspace-pane-shell"][data-view="${view}"]`
                        );
                    }
                    if (kind === "auth-main") {
                        return document.querySelector("main.auth-main-content");
                    }
                    return document.scrollingElement;
                };
                const element = resolveElement();
                if (!element) {
                    throw new Error(`Missing scroll element for ${kind}.`);
                }
                element.scrollTo({ top: targetScrollTop, behavior: "instant" });
                return element.scrollTop;
            }""",
            {"view": view, "kind": kind, "targetScrollTop": target_scroll_top},
        )
    )


def _assert_pool_header_stays_fixed(
    page: Page,
    *,
    pool_test_id: str,
    route_label: str,
) -> None:
    header = page.locator(f'[data-test="{pool_test_id}-header"]')
    scroll_body = page.locator(f'[data-test="{pool_test_id}-scroll-body"]')
    expect(header).to_be_visible(timeout=60_000)
    expect(scroll_body).to_be_visible(timeout=60_000)
    before_header = header.bounding_box()
    if before_header is None:
        raise AssertionError(
            f"{route_label}: missing {pool_test_id} header bounding box before scroll."
        )
    scroll_metrics = scroll_body.evaluate(
        """(element) => ({
            scrollHeight: element.scrollHeight,
            clientHeight: element.clientHeight,
            scrollTop: element.scrollTop,
        })"""
    )
    if scroll_metrics["scrollHeight"] <= scroll_metrics["clientHeight"] + 1:
        raise AssertionError(
            f"{route_label}: expected {pool_test_id} list body to overflow internally, "
            f"got scrollHeight={scroll_metrics['scrollHeight']:.2f}px and "
            f"clientHeight={scroll_metrics['clientHeight']:.2f}px."
        )
    scroll_body.evaluate(
        """(element) => {
            element.scrollTo({
                top: Math.max(24, element.scrollHeight - element.clientHeight),
                behavior: 'instant',
            });
            return element.scrollTop;
        }"""
    )
    page.wait_for_timeout(200)
    after_header = header.bounding_box()
    if after_header is None:
        raise AssertionError(
            f"{route_label}: missing {pool_test_id} header bounding box after scroll."
        )
    after_scroll_top = scroll_body.evaluate("(element) => element.scrollTop")
    assert after_scroll_top > 0, (
        f"{route_label}: expected {pool_test_id} list body to scroll, got scrollTop={after_scroll_top:.2f}px."
    )
    assert abs(after_header["y"] - before_header["y"]) <= STICKY_TOLERANCE, (
        f"{route_label}: expected {pool_test_id} header to stay fixed while the list body scrolls, "
        f"before={before_header['y']:.2f}px after={after_header['y']:.2f}px."
    )
    scroll_body.evaluate("(element) => element.scrollTo({ top: 0, behavior: 'instant' })")


def _assert_workspace_scroll_promotes_operational_band(
    page: Page,
    *,
    view: str,
    pool_lane_test_id: str,
    primary_lane_test_id: str,
    route_label: str,
    screenshot_name: str,
) -> None:
    toolbar = page.locator(f'[data-ui="planner-workspace-toolbar-shell"][data-view="{view}"]')
    pool_lane = page.locator(f'[data-test="{pool_lane_test_id}"]')
    primary_lane = page.locator(f'[data-test="{primary_lane_test_id}"]')
    auth_main = page.locator("main.auth-main-content")
    expect(toolbar).to_be_visible(timeout=60_000)
    expect(pool_lane).to_be_visible(timeout=60_000)
    expect(primary_lane).to_be_visible(timeout=60_000)
    expect(auth_main).to_be_visible(timeout=60_000)
    before_metrics = page.evaluate(
        """({ view, poolLaneTestId, primaryLaneTestId }) => {
            const toolbar = document.querySelector(
                `[data-ui="planner-workspace-toolbar-shell"][data-view="${view}"]`
            );
            const poolLane = document.querySelector(`[data-test="${poolLaneTestId}"]`);
            const primaryLane = document.querySelector(`[data-test="${primaryLaneTestId}"]`);
            const authMain = document.querySelector("main.auth-main-content");
            if (!toolbar || !poolLane || !primaryLane || !authMain) {
                throw new Error("Missing live planner workspace elements for scroll proof.");
            }
            const toolbarRect = toolbar.getBoundingClientRect();
            const poolRect = poolLane.getBoundingClientRect();
            const primaryRect = primaryLane.getBoundingClientRect();
            return {
                scrollTop: authMain.scrollTop,
                maxScrollTop: authMain.scrollHeight - authMain.clientHeight,
                toolbarTop: toolbarRect.top,
                toolbarBottom: toolbarRect.bottom,
                poolTop: poolRect.top,
                primaryTop: primaryRect.top,
            };
        }""",
        {
            "view": view,
            "poolLaneTestId": pool_lane_test_id,
            "primaryLaneTestId": primary_lane_test_id,
        },
    )
    target_scroll_top = min(float(before_metrics["maxScrollTop"]), 420.0)
    if target_scroll_top <= 180.0:
        raise AssertionError(
            f"{route_label}: expected enough planner-page overflow to move past the top panel, "
            f"got maxScrollTop={before_metrics['maxScrollTop']:.2f}px."
        )
    auth_main.evaluate(
        """(element, targetScrollTop) => {
            element.scrollTo({ top: targetScrollTop, behavior: "instant" });
            return element.scrollTop;
        }""",
        target_scroll_top,
    )
    page.wait_for_timeout(250)
    after_metrics = page.evaluate(
        """({ view, poolLaneTestId, primaryLaneTestId }) => {
            const toolbar = document.querySelector(
                `[data-ui="planner-workspace-toolbar-shell"][data-view="${view}"]`
            );
            const poolLane = document.querySelector(`[data-test="${poolLaneTestId}"]`);
            const primaryLane = document.querySelector(`[data-test="${primaryLaneTestId}"]`);
            const authMain = document.querySelector("main.auth-main-content");
            if (!toolbar || !poolLane || !primaryLane || !authMain) {
                throw new Error("Missing live planner workspace elements after scroll proof.");
            }
            const toolbarRect = toolbar.getBoundingClientRect();
            const poolRect = poolLane.getBoundingClientRect();
            const primaryRect = primaryLane.getBoundingClientRect();
            return {
                scrollTop: authMain.scrollTop,
                toolbarTop: toolbarRect.top,
                toolbarBottom: toolbarRect.bottom,
                poolTop: poolRect.top,
                primaryTop: primaryRect.top,
            };
        }""",
        {
            "view": view,
            "poolLaneTestId": pool_lane_test_id,
            "primaryLaneTestId": primary_lane_test_id,
        },
    )
    assert after_metrics["scrollTop"] > 180.0, (
        f"{route_label}: expected the authenticated planner page to scroll downward, "
        f"got scrollTop={after_metrics['scrollTop']:.2f}px."
    )
    assert after_metrics["toolbarTop"] < before_metrics["toolbarTop"] - 140.0, (
        f"{route_label}: expected the large top panel to scroll away before the toolbar settles "
        f"into the working band, before={before_metrics['toolbarTop']:.2f}px "
        f"after={after_metrics['toolbarTop']:.2f}px."
    )
    assert after_metrics["primaryTop"] < before_metrics["primaryTop"] - 140.0, (
        f"{route_label}: expected the main workspace lane to stay on the page scroll path, "
        f"before={before_metrics['primaryTop']:.2f}px after={after_metrics['primaryTop']:.2f}px."
    )
    assert abs(after_metrics["poolTop"] - after_metrics["toolbarBottom"] - 16.0) <= 4.0, (
        f"{route_label}: expected the rail to stay just below the sticky toolbar after page scroll, "
        f"toolbarBottom={after_metrics['toolbarBottom']:.2f}px poolTop={after_metrics['poolTop']:.2f}px."
    )
    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)
    auth_main.evaluate("(element) => element.scrollTo({ top: 0, behavior: 'instant' })")


def _assert_split_workspace_alignment_during_lane_scroll(
    page: Page,
    *,
    pool_test_id: str,
    primary_lane_test_id: str,
    scroll_selector: str,
    route_label: str,
    screenshot_name: str,
) -> None:
    pool = page.locator(f'[data-test="{pool_test_id}"]')
    primary_lane = page.locator(f'[data-test="{primary_lane_test_id}"]')
    scroll_element = page.locator(scroll_selector)
    expect(pool).to_be_visible(timeout=60_000)
    expect(primary_lane).to_be_visible(timeout=60_000)
    expect(scroll_element).to_be_visible(timeout=60_000)
    before_pool = pool.bounding_box()
    before_lane = primary_lane.bounding_box()
    if before_pool is None or before_lane is None:
        raise AssertionError(
            f"{route_label}: missing pool or primary-lane bounding box before lane scroll."
        )
    scroll_metrics = scroll_element.evaluate(
        """(element) => ({
            scrollHeight: element.scrollHeight,
            clientHeight: element.clientHeight,
            scrollTop: element.scrollTop,
        })"""
    )
    if scroll_metrics["scrollHeight"] <= scroll_metrics["clientHeight"] + 1:
        raise AssertionError(
            f"{route_label}: expected {scroll_selector} to overflow internally, "
            f"got scrollHeight={scroll_metrics['scrollHeight']:.2f}px and "
            f"clientHeight={scroll_metrics['clientHeight']:.2f}px."
        )
    target_scroll_top = min(
        scroll_metrics["scrollHeight"] - scroll_metrics["clientHeight"],
        220,
    )
    reached_scroll_top = scroll_element.evaluate(
        """(element, targetScrollTop) => {
            element.scrollTo({ top: targetScrollTop, behavior: "instant" });
            return element.scrollTop;
        }""",
        target_scroll_top,
    )
    page.wait_for_timeout(200)
    after_pool = pool.bounding_box()
    after_lane = primary_lane.bounding_box()
    if after_pool is None or after_lane is None:
        raise AssertionError(
            f"{route_label}: missing pool or primary-lane bounding box after lane scroll."
        )
    assert reached_scroll_top > 0, (
        f"{route_label}: expected {scroll_selector} to scroll internally, "
        f"got scrollTop={reached_scroll_top:.2f}px."
    )
    assert abs(after_pool["y"] - before_pool["y"]) <= STICKY_TOLERANCE, (
        f"{route_label}: expected {pool_test_id} to stay vertically stable while the workspace "
        f"lane scrolls, before={before_pool['y']:.2f}px after={after_pool['y']:.2f}px."
    )
    assert abs(after_lane["y"] - before_lane["y"]) <= STICKY_TOLERANCE, (
        f"{route_label}: expected {primary_lane_test_id} shell to stay vertically stable while its "
        f"content scrolls, before={before_lane['y']:.2f}px after={after_lane['y']:.2f}px."
    )
    assert (
        abs((after_lane["y"] - after_pool["y"]) - (before_lane["y"] - before_pool["y"]))
        <= STICKY_TOLERANCE
    ), (
        f"{route_label}: expected the desktop split-workspace panel relationship to stay preserved "
        f"during internal scroll."
    )
    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)
    scroll_element.evaluate("(element) => element.scrollTo({ top: 0, behavior: 'instant' })")


def _assert_width_band_grouping_shell(
    page: Page,
    *,
    route_label: str,
    width: int,
    height: int,
    width_label: str,
    screenshot_name: str,
) -> None:
    _set_viewport(page, width=width, height=height)
    _wait_for_grouping_surface(page)
    _assert_workspace_body_visible_below_toolbar(
        page,
        view="groups",
        body_test_ids=["grouping-student-pool", "grouping-board-lane"],
        route_label=route_label,
        width_label=width_label,
        screenshot_name=screenshot_name,
    )


def _assert_width_band_seating_shell(
    page: Page,
    *,
    route_label: str,
    width: int,
    height: int,
    width_label: str,
    screenshot_name: str,
) -> None:
    _set_viewport(page, width=width, height=height)
    _wait_for_seating_surface(page)
    _assert_workspace_body_visible_below_toolbar(
        page,
        view="seats",
        body_test_ids=["seating-student-pool", "seating-workspace-lane", "room-canvas-viewport"],
        route_label=route_label,
        width_label=width_label,
        screenshot_name=screenshot_name,
    )


def _assert_pool_stays_sticky_during_workspace_scroll(
    page: Page,
    *,
    view: str,
    pool_test_id: str,
    route_label: str,
    screenshot_name: str,
) -> None:
    pool = page.locator(f'[data-test="{pool_test_id}"]')
    header = page.locator(f'[data-test="{pool_test_id}-header"]')
    expect(pool).to_be_visible(timeout=60_000)
    before_pool = pool.bounding_box()
    before_header = header.bounding_box()
    if before_pool is None or before_header is None:
        raise AssertionError(
            f"{route_label}: missing {pool_test_id} bounding box before workspace scroll."
        )
    scroll_context = _resolve_scroll_context(page, view=view)
    max_scroll_top = float(scroll_context["scrollHeight"]) - float(scroll_context["clientHeight"])
    first_target_scroll_top = min(max_scroll_top, 220)
    first_scroll_top = _scroll_context_to(
        page,
        view=view,
        kind=str(scroll_context["kind"]),
        target_scroll_top=first_target_scroll_top,
    )
    page.wait_for_timeout(200)
    first_pool = pool.bounding_box()
    first_header = header.bounding_box()
    if first_pool is None or first_header is None:
        raise AssertionError(
            f"{route_label}: missing {pool_test_id} bounding box after first workspace scroll."
        )
    assert first_scroll_top >= first_target_scroll_top - 1, (
        f"{route_label}: expected {scroll_context['kind']} scroll context to move near "
        f"{first_target_scroll_top:.2f}px, got {first_scroll_top:.2f}px."
    )
    second_target_scroll_top = min(max_scroll_top, first_target_scroll_top + 140)
    if second_target_scroll_top <= first_target_scroll_top + 16:
        raise AssertionError(
            f"{route_label}: expected enough additional {scroll_context['kind']} overflow to prove "
            f"sticky persistence, got maxScrollTop={max_scroll_top:.2f}px."
        )
    second_scroll_top = _scroll_context_to(
        page,
        view=view,
        kind=str(scroll_context["kind"]),
        target_scroll_top=second_target_scroll_top,
    )
    page.wait_for_timeout(200)
    second_pool = pool.bounding_box()
    second_header = header.bounding_box()
    if second_pool is None or second_header is None:
        raise AssertionError(
            f"{route_label}: missing {pool_test_id} bounding box after second workspace scroll."
        )
    assert second_scroll_top >= second_target_scroll_top - 1, (
        f"{route_label}: expected {scroll_context['kind']} scroll context to move near "
        f"{second_target_scroll_top:.2f}px, got {second_scroll_top:.2f}px."
    )
    step_size = 120.0
    sticky_samples = [(first_scroll_top, first_pool["y"], first_header["y"])]
    probe_target = second_target_scroll_top
    while probe_target < max_scroll_top - 16:
        probe_target = min(max_scroll_top, probe_target + step_size)
        probe_scroll_top = _scroll_context_to(
            page,
            view=view,
            kind=str(scroll_context["kind"]),
            target_scroll_top=probe_target,
        )
        page.wait_for_timeout(120)
        probe_pool = pool.bounding_box()
        probe_header = header.bounding_box()
        if probe_pool is None or probe_header is None:
            raise AssertionError(
                f"{route_label}: missing {pool_test_id} bounding box while probing sticky engagement."
            )
        sticky_samples.append((probe_scroll_top, probe_pool["y"], probe_header["y"]))
    engaged_index = None
    for index in range(1, len(sticky_samples)):
        previous_sample = sticky_samples[index - 1]
        current_sample = sticky_samples[index]
        if (
            abs(current_sample[1] - previous_sample[1]) <= STICKY_TOLERANCE
            and previous_sample[0] < max_scroll_top - 16
        ):
            engaged_index = index
            break
    assert first_pool["y"] < before_pool["y"] - 24, (
        f"{route_label}: expected {pool_test_id} rail to move upward toward its sticky resting band "
        f"during the first {view} workspace scroll, before={before_pool['y']:.2f}px "
        f"after={first_pool['y']:.2f}px."
    )
    if engaged_index is None:
        raise AssertionError(
            f"{route_label}: expected {pool_test_id} rail to reach a sticky resting band during "
            f"{view} workspace scroll, samples={sticky_samples!r}, maxScrollTop={max_scroll_top:.2f}px."
        )
    engaged_sample = sticky_samples[engaged_index]
    engaged_previous_sample = sticky_samples[engaged_index - 1]
    assert abs(engaged_sample[1] - engaged_previous_sample[1]) <= STICKY_TOLERANCE, (
        f"{route_label}: expected {pool_test_id} rail to stop moving once sticky engaged during "
        f"{view} workspace scroll, previous={engaged_previous_sample[1]:.2f}px "
        f"current={engaged_sample[1]:.2f}px."
    )
    assert abs(engaged_sample[2] - engaged_previous_sample[2]) <= STICKY_TOLERANCE, (
        f"{route_label}: expected {pool_test_id} header to stay attached to the sticky rail once "
        f"engaged during {view} workspace scroll, previous={engaged_previous_sample[2]:.2f}px "
        f"current={engaged_sample[2]:.2f}px."
    )
    page.screenshot(path=str(ARTIFACTS_DIR / screenshot_name), full_page=True)
    _scroll_context_to(page, view=view, kind=str(scroll_context["kind"]), target_scroll_top=0)


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


def _verify_authenticated_route(page: Page, *, base_url: str, roster_name: str) -> None:
    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
    _set_viewport(page, width=DESKTOP_WIDTH, height=DESKTOP_HEIGHT)
    _dismiss_upgrade_prompt_if_present(page)
    open_class_workspace(page, roster_name=roster_name)
    _assert_width_band_grouping_shell(
        page,
        route_label="authenticated route",
        width=INTERMEDIATE_WIDTH,
        height=INTERMEDIATE_HEIGHT,
        width_label="1279x900",
        screenshot_name="auth-grouping-shell-1279.png",
    )
    _assert_width_band_grouping_shell(
        page,
        route_label="authenticated route",
        width=LAPTOP_WIDTH,
        height=LAPTOP_HEIGHT,
        width_label="1366x768",
        screenshot_name="auth-grouping-shell-1366.png",
    )
    _assert_width_band_grouping_shell(
        page,
        route_label="authenticated route",
        width=DESKTOP_WIDTH,
        height=DESKTOP_HEIGHT,
        width_label="1440x900",
        screenshot_name="auth-grouping-shell-1440.png",
    )
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
    _set_viewport(page, width=LAPTOP_WIDTH, height=LAPTOP_HEIGHT)
    _assert_pool_header_stays_fixed(
        page,
        pool_test_id="grouping-student-pool",
        route_label="authenticated route grouping pool",
    )
    _set_group_count(page, target_count=GROUPING_OVERFLOW_COUNT)
    _assert_workspace_scroll_promotes_operational_band(
        page,
        view="groups",
        pool_lane_test_id="grouping-student-pool-lane",
        primary_lane_test_id="grouping-board-lane",
        route_label="authenticated route grouping workspace",
        screenshot_name="auth-grouping-operational-band.png",
    )
    _assert_width_band_seating_shell(
        page,
        route_label="authenticated route",
        width=INTERMEDIATE_WIDTH,
        height=INTERMEDIATE_HEIGHT,
        width_label="1279x900",
        screenshot_name="auth-seating-shell-1279.png",
    )
    _assert_width_band_seating_shell(
        page,
        route_label="authenticated route",
        width=LAPTOP_WIDTH,
        height=LAPTOP_HEIGHT,
        width_label="1366x768",
        screenshot_name="auth-seating-shell-1366.png",
    )
    _assert_width_band_seating_shell(
        page,
        route_label="authenticated route",
        width=DESKTOP_WIDTH,
        height=DESKTOP_HEIGHT,
        width_label="1440x900",
        screenshot_name="auth-seating-shell-1440.png",
    )
    _wait_for_seating_surface(page)
    _assert_pool_header_stays_fixed(
        page,
        pool_test_id="seating-student-pool",
        route_label="authenticated route seating pool",
    )
    _assert_workspace_scroll_promotes_operational_band(
        page,
        view="seats",
        pool_lane_test_id="seating-student-pool-lane",
        primary_lane_test_id="seating-workspace-lane",
        route_label="authenticated route seating workspace",
        screenshot_name="auth-seating-operational-band.png",
    )


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
