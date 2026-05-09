"""Shared Playwright touch-input helpers.

Purpose:
    Provide deterministic browser-level phone gestures for retained proofs that
    need to exercise app-owned touch handlers through Chromium's input path.

Relationships:
    - Used by focused Klassrumskartan PR proofs for small-screen classroom maps.
    - Keeps touch-action evidence and touch input dispatch outside individual
      proof scripts.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def pinch_zoom(
    page: Page, selector: str, *, start_distance: int = 100, end_distance: int = 140
) -> None:
    """Dispatch a two-finger pinch gesture against one visible element.

    The helper intentionally uses Chrome DevTools Protocol touch input instead
    of fabricating DOM TouchEvent objects so retained proofs pass through the
    browser's touch-action arbitration.
    """

    target = page.locator(selector).first
    expect(target).to_be_visible()
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    if box is None:
        raise AssertionError(f"{selector} did not expose a visible bounding box.")

    viewport = page.viewport_size or {"width": box["width"], "height": box["height"]}
    visible_left = max(box["x"], 1)
    visible_top = max(box["y"], 1)
    visible_right = min(box["x"] + box["width"], viewport["width"] - 1)
    visible_bottom = min(box["y"] + box["height"], viewport["height"] - 1)
    if visible_right <= visible_left or visible_bottom <= visible_top:
        raise AssertionError(f"{selector} did not expose a visible viewport intersection.")
    center_x = visible_left + (visible_right - visible_left) / 2
    center_y = visible_top + (visible_bottom - visible_top) / 2
    client = page.context.new_cdp_session(page)

    def touch_points(distance: int) -> list[dict[str, int | float]]:
        return [
            {
                "x": center_x - distance / 2,
                "y": center_y,
                "radiusX": 1,
                "radiusY": 1,
                "force": 1,
                "id": 1,
            },
            {
                "x": center_x + distance / 2,
                "y": center_y,
                "radiusX": 1,
                "radiusY": 1,
                "force": 1,
                "id": 2,
            },
        ]

    try:
        client.send(
            "Emulation.setTouchEmulationEnabled",
            {"enabled": True, "maxTouchPoints": 2},
        )
        client.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": touch_points(start_distance)},
        )
        for distance in (int((start_distance + end_distance) / 2), end_distance):
            client.send(
                "Input.dispatchTouchEvent",
                {"type": "touchMove", "touchPoints": touch_points(distance)},
            )
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    finally:
        client.detach()
    page.wait_for_timeout(100)


def assert_touch_action(page: Page, selector: str, *, expected: str = "pan-x pan-y") -> None:
    """Assert the touched element declares the browser gesture-ownership contract."""

    target = page.locator(selector).first
    expect(target).to_be_visible()
    target.scroll_into_view_if_needed()
    actual = target.evaluate("element => getComputedStyle(element).touchAction")
    normalized = " ".join(str(actual).split())
    if normalized != expected:
        raise AssertionError(f"{selector} touch-action was {normalized!r}, expected {expected!r}.")
