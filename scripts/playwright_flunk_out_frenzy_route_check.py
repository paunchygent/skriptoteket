"""Live browser proof for the Flunk-Out Frenzy curated-app route.

This script logs in through the protected Flunk-Out Frenzy route, verifies that
the bespoke shell reaches a bootstrap-ready state, opens the settings overlay
to confirm bootstrap metadata is visible, and starts the local runtime to prove
the mounted playfield appears without falling back to the generic app host.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

APP_PATH = "/apps/games.flunk_out_frenzy"
ARTIFACTS_DIR = Path(".artifacts/flunk-out-frenzy-route-check")


def login_to_flunk_out_frenzy(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Log in through the protected game route and wait for the shell to load."""

    for attempt in range(3):
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        try:
            wait_for_shell_ready(page)
            expect(page).to_have_url(re.compile(re.escape(APP_PATH) + r"$"))
            return
        except AssertionError:
            login_dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
            if login_dialog.count() > 0:
                expect(login_dialog).to_be_visible()
                login_dialog.get_by_label("E-post").fill(email)
                login_dialog.get_by_label("Lösenord").fill(password)
                login_dialog.get_by_role(
                    "button", name=re.compile(r"Logga in", re.IGNORECASE)
                ).click()
                page.wait_for_timeout(1000)
            elif attempt == 0:
                page.goto(f"{base_url}/login", wait_until="domcontentloaded")
                login_page_dialog = page.get_by_role(
                    "dialog", name=re.compile(r"Logga in", re.IGNORECASE)
                )
                if login_page_dialog.count() > 0:
                    expect(login_page_dialog).to_be_visible()
                    login_page_dialog.get_by_label("E-post").fill(email)
                    login_page_dialog.get_by_label("Lösenord").fill(password)
                    login_page_dialog.get_by_role(
                        "button", name=re.compile(r"Logga in", re.IGNORECASE)
                    ).click()
                    page.wait_for_timeout(1000)
            if attempt == 2:
                raise
            page.wait_for_timeout(1000)


def wait_for_shell_ready(page: Page) -> None:
    """Wait for either a ready shell or a visible bootstrap error."""

    ready_state = page.locator('[data-test="bootstrap-ready"]')
    error_state = page.locator('[data-test="bootstrap-error"]')

    for _ in range(60):
        if ready_state.count() > 0 and ready_state.first.is_visible():
            return
        if error_state.count() > 0 and error_state.first.is_visible():
            raise AssertionError(
                f"Flunk-Out Frenzy bootstrap failed: {error_state.first.inner_text()}"
            )
        page.wait_for_timeout(500)

    raise AssertionError("Flunk-Out Frenzy did not reach a bootstrap-ready state.")


def verify_bootstrap_overlay(page: Page) -> None:
    """Open the settings overlay and confirm the typed bootstrap metadata renders."""

    page.locator('[data-test="settings-toggle"]').click()
    settings_panel = page.locator('[data-test="settings-panel"]')
    expect(settings_panel).to_be_visible()
    expect(
        settings_panel.get_by_text("flunk_out_frenzy.prototype_alpha.v1", exact=True)
    ).to_be_visible()
    settings_panel.get_by_role("button", name="Stäng").click()
    expect(settings_panel).to_be_hidden()


def verify_runtime_start(page: Page) -> None:
    """Start the runtime and confirm the mounted playfield appears."""

    page.get_by_role("button", name=re.compile(r"^Start$", re.IGNORECASE)).click()
    runtime_host = page.locator('[data-test="runtime-host-placeholder"]')
    expect(runtime_host).to_have_attribute("data-runtime-load-state", "ready", timeout=30000)
    expect(runtime_host).to_have_attribute("data-runtime-mounted", "true", timeout=30000)
    expect(page.locator('[data-test="runtime-renderer-canvas"]')).to_be_visible()


def main() -> None:
    """Run the Flunk-Out Frenzy route proof against the configured SPA base URL."""

    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        login_to_flunk_out_frenzy(
            page,
            base_url=config.base_url.rstrip("/"),
            email=config.email,
            password=config.password,
        )
        verify_bootstrap_overlay(page)
        verify_runtime_start(page)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "flunk-out-frenzy-route.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"playwright-flunk-out-frenzy: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
