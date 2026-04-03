"""Live proof for the shared secondary subrail in Mina filer.

Purpose:
    Verify that the shared local segmented rails in Mina filer render and
    behave correctly in the live Vault UI, including visible dividers,
    tightened label chrome, and the search/sort height relationship.

Relationships:
    - uses the shared Playwright config for local credentials and base URL
    - validates the shared `UiSegmentedToggle` subrail variant outside
      Klassrumskartan so the pattern stays cross-app
    - writes a screenshot under `.artifacts/vault-sort-subrail-check/`
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/vault-sort-subrail-check")


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


def main() -> None:
    """Verify the live Vault sort switch uses the shared secondary subrail."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=config.email, password=config.password)
        page.goto(f"{base_url}/vault", wait_until="domcontentloaded")

        expect(page.get_by_role("heading", name="Mina filer", exact=True)).to_be_visible()
        page.wait_for_timeout(250)

        expect(page.get_by_text("Aktiva filer och papperskorg.", exact=True)).to_have_count(0)
        expect(page.get_by_text("Sortera", exact=True)).to_have_count(0)
        expect(page.get_by_text("Sök", exact=True)).to_have_count(0)

        state_switch = page.locator('[data-test="vault-state-switch"]')
        expect(state_switch).to_be_visible()

        sort_switch = page.locator('[data-test="vault-sort-switch"]')
        expect(sort_switch).to_be_visible()
        expect(sort_switch.locator('[data-test="vault-sort-newest"]')).to_have_attribute(
            "aria-checked",
            "true",
        )
        for test_id in ["vault-sort-name", "vault-sort-size"]:
            border_left_width = sort_switch.locator(f'[data-test="{test_id}"]').evaluate(
                "element => window.getComputedStyle(element).borderLeftWidth"
            )
            if border_left_width == "0px":
                raise AssertionError("Vault sort switch lost an interior divider.")

        sort_switch.locator('[data-test="vault-sort-name"]').click()
        expect(sort_switch.locator('[data-test="vault-sort-name"]')).to_have_attribute(
            "aria-checked",
            "true",
        )
        expect(sort_switch.locator('[data-test="vault-sort-size"]')).to_be_visible()

        search_input = page.locator('input[type="search"]')
        search_box = search_input.bounding_box()
        sort_box = sort_switch.bounding_box()
        if search_box is None or sort_box is None:
            raise AssertionError("Expected visible search and sort controls in Mina filer.")
        if abs(search_box["height"] - sort_box["height"]) > 2.0:
            raise AssertionError(
                f"Vault sort switch height drifted from search bar height: {sort_box['height']:.2f}px vs {search_box['height']:.2f}px."
            )

        page.screenshot(path=str(ARTIFACTS_DIR / "vault-sort-subrail.png"), full_page=True)
        context.close()
        browser.close()

    print(f"playwright-vault-subrail: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
