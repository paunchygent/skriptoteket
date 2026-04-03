"""Live browser proof for the Flunk-Out Frenzy curated-app route."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._playwright_flunk_out_frenzy import (
    login_to_flunk_out_frenzy,
    verify_runtime_start,
)

ARTIFACTS_DIR = Path(".artifacts/flunk-out-frenzy-route-check")


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


def main() -> None:
    """Run the Flunk-Out Frenzy route proof against the configured SPA base URL."""

    config = get_config()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
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
