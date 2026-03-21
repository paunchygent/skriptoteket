"""Reusable Playwright smoke for the Klassrumskartan planner app.

This script is the app-specific baseline for future classroom planner browser
checks. It reuses the repo's shared Playwright config and Chromium launch
fallback, logs in through the protected app route, creates a small real class
list and classroom, opens the planner, and verifies that the core workspace can
be reached without relying on PR-specific flows.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

APP_PATH = "/apps/classroom.group-seating-studio"
ARTIFACTS_DIR = Path(".artifacts/classroom-planner-smoke")


def _wait_for_app_heading(page: Any) -> None:
    """Poll for the planner heading through the SPA transition after login."""

    app_heading = page.locator("main").get_by_text("Klassrumskartan", exact=True)
    for _ in range(30):
        if app_heading.count() > 0:
            return
        page.wait_for_timeout(500)

    raise AssertionError("Klassrumskartan did not render after protected-route login.")


def _login_to_app(page: Any, *, base_url: str, email: str, password: str) -> None:
    """Open the protected app route and complete the standard SPA login modal."""

    page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")

    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    if dialog.count() > 0:
        expect(dialog).to_be_visible()
        dialog.get_by_label("E-post").fill(email)
        dialog.get_by_label("Lösenord").fill(password)
        dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible(timeout=15_000)

    _wait_for_app_heading(page)


def _create_roster(page: Any, *, roster_name: str) -> None:
    """Create a deterministic class list through the live roster modal."""

    page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(roster_name)))).to_be_visible()


def _create_template(page: Any, *, template_name: str) -> None:
    """Create a tiny classroom through the live room modal."""

    page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    expect(page.get_by_role("heading", name=re.compile(re.escape(template_name)))).to_be_visible()


def _open_workspace(page: Any) -> None:
    """Open the planner workspace from the selection gate."""

    open_button = page.get_by_role("button", name=re.compile(r"Öppna planeringen", re.IGNORECASE))
    expect(open_button).to_be_enabled()
    open_button.click()
    expect(page.get_by_role("button", name=re.compile(r"Gruppvy", re.IGNORECASE))).to_be_visible()
    expect(
        page.get_by_role("button", name=re.compile(r"Sittplatser", re.IGNORECASE))
    ).to_be_visible()


def _open_student_metadata(page: Any) -> None:
    """Open one student's seating drawer to prove the planner is interactive."""

    page.get_by_role("button", name=re.compile(r"Sittplatser", re.IGNORECASE)).click()
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).click()
    expect(page.get_by_text("Elevanteckningar", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ada Lovelace", re.IGNORECASE))
    ).to_be_visible()


def main() -> None:
    """Run the reusable Klassrumskartan browser smoke."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW Klass {run_suffix}"
    template_name = f"PW Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        _login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        _create_roster(page, roster_name=roster_name)
        _create_template(page, template_name=template_name)
        _open_workspace(page)
        _open_student_metadata(page)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "classroom-planner-smoke.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
