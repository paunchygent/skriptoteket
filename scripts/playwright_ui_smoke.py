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
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
    ).to_be_visible()


def _open_help_panel(page: object) -> object | None:
    help_button = page.get_by_role("button", name=re.compile(r"Hjälp", re.IGNORECASE))
    if help_button.count() == 0:
        return None

    help_button.first.click()
    help_panel = page.locator("#help-panel")
    expect(help_panel).to_be_visible()
    expect(help_panel.get_by_role("heading", name="Hjälp")).to_be_visible()
    return help_panel


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        device = playwright.devices["iPhone 12"]
        browser = _launch_chromium(playwright)
        context = browser.new_context(**device)
        page = context.new_page()

        # Logged-out help panel (mobile)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        help_panel = _open_help_panel(page)
        if help_panel:
            page.screenshot(path=str(artifacts_dir / "help-logged-out-mobile.png"), full_page=False)
            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        # Login
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "home.png"), full_page=True)

        # Mobile sidebar help + logout
        menu_btn = page.get_by_role("button", name="Meny")
        menu_btn.click()
        sidebar = page.locator("aside.sidebar.is-open")
        expect(sidebar).to_be_visible()

        sidebar_help = sidebar.get_by_role("button", name="Hjälp")
        if sidebar_help.count() > 0:
            sidebar_help.click()
            help_panel = page.locator("#help-panel")
            expect(help_panel).to_be_visible()
            page.screenshot(path=str(artifacts_dir / "help-logged-in-mobile.png"), full_page=False)
            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        nav_link = sidebar.get_by_role("link", name=re.compile(r"Katalog", re.IGNORECASE))
        if nav_link.count() > 0:
            expect(nav_link).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "mobile-nav.png"), full_page=True)

        # Browse professions + categories
        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Bläddra verktyg", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-professions.png"), full_page=True)

        profession_list = page.get_by_role("main").locator("ul").first
        first_profession = profession_list.get_by_role("link").first
        first_profession.click()
        expect(page.get_by_text("Välj en kategori")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "browse-categories.png"), full_page=True)

        context.close()
        browser.close()

        # Desktop sanity check
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        help_panel = _open_help_panel(page)
        if help_panel:
            page.screenshot(path=str(artifacts_dir / "help-desktop.png"), full_page=False)
            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Bläddra verktyg", re.IGNORECASE))
        ).to_be_visible()

        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "admin-tools-desktop.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright UI smoke screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
