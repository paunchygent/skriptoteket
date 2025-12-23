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

    artifacts_dir = Path(".artifacts/st-11-18-editor-maintainers")
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
        expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()

        # Open admin tools list
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Verktyg", re.IGNORECASE))).to_be_visible()

        tool_list = page.locator("section").locator("ul").first
        action_links = tool_list.get_by_role("link", name=re.compile(r"Redigera|Granska", re.IGNORECASE))
        if action_links.count() == 0:
            raise RuntimeError("No admin tools available to open in editor.")

        action_links.first.click()
        page.wait_for_url("**/admin/tools/**", wait_until="domcontentloaded")
        expect(page.get_by_text("Källkod")).to_be_visible()

        # Version history should not trigger navigation (soft load).
        current_url = page.url
        page.get_by_role("button", name=re.compile(r"Öppna sparade", re.IGNORECASE)).click()
        history_title = page.get_by_role(
            "heading",
            name=re.compile(r"Öppna sparade", re.IGNORECASE),
        )
        expect(history_title).to_be_visible()
        history_drawer = page.locator("aside", has=history_title)
        if history_drawer.locator("li").count() > 0:
            first_row = history_drawer.locator("li").first
            first_row.get_by_role("button").first.click()
            expect(page).to_have_url(current_url)

        page.get_by_role(
            "button",
            name=re.compile(r"Redigeringsbehörigheter", re.IGNORECASE),
        ).click()

        drawer_title = page.get_by_role(
            "heading",
            name=re.compile(r"Ändra redigeringsbehörigheter", re.IGNORECASE),
        )
        expect(drawer_title).to_be_visible()
        drawer = page.locator("aside", has=drawer_title)

        maintainer_row = drawer.locator("li").filter(has_text=email)
        if maintainer_row.count() > 0:
            maintainer_row.get_by_role("button", name=re.compile(r"Ta bort", re.IGNORECASE)).click()
            expect(maintainer_row).to_have_count(0)

        drawer.get_by_label("E-post").fill(email)
        drawer.get_by_role("button", name=re.compile(r"Lägg till", re.IGNORECASE)).click()
        expect(maintainer_row).to_have_count(1)
        page.screenshot(path=str(artifacts_dir / "maintainers-added.png"), full_page=True)

        maintainer_row.get_by_role("button", name=re.compile(r"Ta bort", re.IGNORECASE)).click()
        expect(maintainer_row).to_have_count(0)
        page.screenshot(path=str(artifacts_dir / "maintainers-removed.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
