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
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-11-15-spa-my-tools-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Login (SPA)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible()

        # My tools view
        page.goto(f"{base_url}/my-tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Mina verktyg", re.IGNORECASE))).to_be_visible()

        empty_state = page.get_by_text("Du har inga verktyg att underhålla ännu.")
        if empty_state.count() > 0 and empty_state.is_visible():
            page.screenshot(path=str(artifacts_dir / "my-tools-empty.png"), full_page=True)
        else:
            tool_list = page.locator("main ul.border-navy").first
            expect(tool_list).to_be_visible()
            rows = tool_list.locator("li")
            expect(rows.first).to_be_visible()

            first_row = rows.first
            status_label = first_row.get_by_text(
                re.compile(r"Publicerad|Ej publicerad", re.IGNORECASE)
            )
            expect(status_label).to_be_visible()

            edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
            if edit_link.count() > 0:
                edit_link.click()
                page.wait_for_url("**/admin/tools/**", wait_until="domcontentloaded")
                page.screenshot(path=str(artifacts_dir / "my-tools-editor.png"), full_page=True)
            else:
                page.screenshot(path=str(artifacts_dir / "my-tools-list.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
