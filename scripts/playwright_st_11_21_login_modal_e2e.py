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


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-11-21-login-modal-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Home CTA opens modal (logged out)
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        hero_login = page.locator("main").get_by_role(
            "button", name=re.compile(r"Logga in", re.IGNORECASE)
        )
        expect(hero_login).to_be_visible()
        hero_login.click()

        dialog = page.locator("div[role='dialog']")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_label("E-post")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "home-login-modal.png"), full_page=True)

        # Close modal by clicking the overlay background
        page.mouse.click(10, 10)
        expect(dialog).to_have_count(0)

        # Header login opens modal on a non-home route
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        header_login = page.locator("header").get_by_role(
            "button", name=re.compile(r"Logga in", re.IGNORECASE)
        )
        expect(header_login).to_be_visible()
        header_login.click()

        dialog = page.locator("div[role='dialog']")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_label("E-post")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "header-login-modal.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
