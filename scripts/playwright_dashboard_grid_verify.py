"""Verify HomeView dashboard grid alignment with and without focus mode.

Captures screenshots to verify:
1. Tool cards and action cards have the same column count
2. Focus mode properly expands grids to add a 4th column
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def _find_chromium_headless_shell() -> str | None:
    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None

    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        for subdir in [
            "chrome-headless-shell-mac-arm64",
            "chrome-headless-shell-mac-x64",
        ]:
            binary = candidate / subdir / "chrome-headless-shell"
            if binary.is_file():
                return str(binary)

    return None


def _launch_chromium(playwright: object) -> object:
    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as exc:
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        message = str(exc)
        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
    ).to_be_visible()


def _wait_for_transition(page: object) -> None:
    # Wait for CSS transitions (expand-left uses 300ms)
    page.wait_for_timeout(400)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/dashboard-grid")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        # Desktop viewport: 1440px wide for 3 columns normally, 4 in focus mode
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _wait_for_transition(page)

        # Screenshot 1: Normal mode (sidebar visible)
        page.screenshot(path=str(artifacts_dir / "dashboard-normal.png"), full_page=True)
        print(f"Captured: {artifacts_dir / 'dashboard-normal.png'}")

        # Toggle focus mode
        focus_btn = page.get_by_role(
            "button", name=re.compile(r"Aktivera fokusläge", re.IGNORECASE)
        )
        if focus_btn.count() == 0:
            focus_btn = page.get_by_role("button", name=re.compile(r"fokus", re.IGNORECASE))

        if focus_btn.count() > 0:
            focus_btn.first.click()
            _wait_for_transition(page)

            # Screenshot 2: Focus mode (sidebar hidden, grids expanded)
            page.screenshot(path=str(artifacts_dir / "dashboard-focus.png"), full_page=True)
            print(f"Captured: {artifacts_dir / 'dashboard-focus.png'}")

            # Toggle back to normal
            exit_focus_btn = page.get_by_role(
                "button", name=re.compile(r"Avsluta fokusläge", re.IGNORECASE)
            )
            if exit_focus_btn.count() > 0:
                exit_focus_btn.first.click()
                _wait_for_transition(page)
                page.screenshot(path=str(artifacts_dir / "dashboard-restored.png"), full_page=True)
                print(f"Captured: {artifacts_dir / 'dashboard-restored.png'}")
        else:
            print("Focus mode button not found - skipping focus mode screenshots")

        context.close()
        browser.close()

    print(f"\nDashboard grid screenshots saved to: {artifacts_dir}")
    print("Verify visually that tool cards and action cards have matching column alignment.")


if __name__ == "__main__":
    main()
