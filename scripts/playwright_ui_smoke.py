"""Canonical Playwright smoke for the shared landing page and auth shell.

This smoke is the repo's broad UI gate for redeploy-style verification. It
checks the public landing page contract, logs in through the shared protected-
route modal flow, and then sweeps a small authenticated route set on both
mobile and desktop viewports.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Browser, Locator, Page, Playwright, expect, sync_playwright
from playwright.sync_api import Error as PlaywrightError

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


def _launch_chromium(playwright: Playwright) -> Browser:
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


def _assert_public_landing(page: Page, *, verify_equal_cta_widths: bool = False) -> None:
    landing_main = page.locator("main").first
    expect(
        page.get_by_role("heading", name=re.compile(r"^Skriptoteket$", re.IGNORECASE))
    ).to_be_visible()
    expect(
        landing_main.get_by_text("Professionellt appbibliotek för lärare", exact=True)
    ).to_be_visible()
    expect(
        landing_main.get_by_text(
            "Logga in och använd appar och verktyg för undervisning, planering och dokumentation.",
            exact=True,
        )
    ).to_be_visible()
    expect(landing_main.get_by_text("Professionellt appbibliotek", exact=True)).to_be_visible()
    expect(landing_main.get_by_text("Dela med kollegor", exact=True)).to_be_visible()
    expect(landing_main.get_by_text("GDPR-säkrad datahantering", exact=True)).to_be_visible()

    hero_login = landing_main.get_by_role("button", name=re.compile(r"^Logga in$", re.IGNORECASE))
    hero_register = landing_main.get_by_role(
        "link", name=re.compile(r"^Skapa konto$", re.IGNORECASE)
    )
    expect(hero_login).to_be_visible()
    expect(hero_register).to_be_visible()

    if not verify_equal_cta_widths:
        return

    login_width = hero_login.evaluate("element => element.getBoundingClientRect().width")
    register_width = hero_register.evaluate("element => element.getBoundingClientRect().width")
    width_diff = abs(login_width - register_width)
    assert width_diff <= 1.0, (
        "Expected landing CTA buttons to keep the same width on desktop. "
        f"Got diff={width_diff:.2f}px (login={login_width:.2f}, register={register_width:.2f})."
    )


def _login(page: Page, *, base_url: str, email: str, password: str) -> None:
    protected_destination = f"{base_url}/browse"
    catalog_heading = page.get_by_role("heading", name=re.compile(r"^Katalog$", re.IGNORECASE))

    for attempt in range(3):
        page.goto(protected_destination, wait_until="domcontentloaded")
        if catalog_heading.count() > 0 and catalog_heading.first.is_visible():
            return

        dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
        if dialog.count() == 0:
            page.wait_for_timeout(750)
            continue

        expect(dialog).to_be_visible(timeout=10_000)
        dialog.get_by_label("E-post").fill(email)
        dialog.get_by_label("Lösenord").fill(password)
        dialog.get_by_role("button", name=re.compile(r"^Logga in", re.IGNORECASE)).click()

        try:
            expect(catalog_heading).to_be_visible(timeout=30_000)
            return
        except AssertionError:
            if attempt == 2:
                raise
            page.wait_for_timeout(1_000)

    raise AssertionError("Protected-route login did not reach the catalog after three attempts.")


def _open_help_panel(page: Page) -> Locator | None:
    help_button = page.get_by_role("button", name=re.compile(r"Hjälp", re.IGNORECASE))
    if help_button.count() == 0:
        return None

    help_button.first.click()
    help_panel = page.locator("#help-panel")
    expect(help_panel).to_be_visible()
    expect(
        help_panel.get_by_role("heading", name=re.compile(r"^Hjälp$", re.IGNORECASE))
    ).to_be_visible()
    return help_panel


def _wait_for_page_fade_in(page: Page) -> None:
    # RouterView transition uses opacity; Playwright "visible" checks do not consider opacity.
    page.wait_for_timeout(250)


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
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        _assert_public_landing(page)
        page.screenshot(path=str(artifacts_dir / "landing-mobile.png"), full_page=True)
        help_panel = _open_help_panel(page)
        if help_panel:
            page.screenshot(path=str(artifacts_dir / "help-logged-out-mobile.png"), full_page=False)
            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        # Login
        _login(page, base_url=base_url, email=email, password=password)
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
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

        # Browse catalog (mobile)
        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "browse-mobile.png"), full_page=True)

        page.goto(f"{base_url}/vault", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"^Mina filer$", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "vault-mobile.png"), full_page=True)

        curated_checkbox = page.get_by_label(re.compile(r"Enbart kurerade appar", re.IGNORECASE))
        if curated_checkbox.count() > 0:
            curated_checkbox.first.check()
            _wait_for_page_fade_in(page)
            page.screenshot(path=str(artifacts_dir / "browse-filters-mobile.png"), full_page=True)

        context.close()
        browser.close()

        # Desktop sanity check
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        _assert_public_landing(page, verify_equal_cta_widths=True)
        page.screenshot(path=str(artifacts_dir / "landing-desktop.png"), full_page=True)
        _login(page, base_url=base_url, email=email, password=password)
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
        help_panel = _open_help_panel(page)
        if help_panel:
            page.screenshot(path=str(artifacts_dir / "help-desktop.png"), full_page=False)
            help_panel.get_by_role("button", name="Stäng").click()
            expect(help_panel).to_be_hidden()

        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)

        page.goto(f"{base_url}/vault", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"^Mina filer$", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "vault-desktop.png"), full_page=True)

        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "admin-tools-desktop.png"), full_page=True)

        page.goto(f"{base_url}/profile", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Profil", re.IGNORECASE))
        ).to_be_visible()
        ai_settings_heading = page.get_by_role(
            "heading", name=re.compile(r"AI-inställningar", re.IGNORECASE)
        ).first
        expect(ai_settings_heading).to_be_visible()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "profile-desktop.png"), full_page=True)
        ai_settings_heading.scroll_into_view_if_needed()
        _wait_for_page_fade_in(page)
        page.screenshot(path=str(artifacts_dir / "profile-ai-settings-desktop.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright UI smoke screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
