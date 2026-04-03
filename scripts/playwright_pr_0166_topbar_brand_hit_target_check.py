"""Focused Playwright proof for the authenticated top-bar brand hit target.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This check verifies that the top-left Skriptoteket brand keeps a stable link
hit target with a pointer cursor after common planner modal flows complete.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import login_to_app, wait_for_app_heading
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0166-topbar-brand-hit-target-check")


def _activate_focus_mode(page: Page) -> None:
    """Reveal the top-bar brand link on standard authenticated routes."""

    focus_button = page.get_by_role("button", name=re.compile(r"Aktivera fokusläge", re.IGNORECASE))
    if focus_button.count() > 0:
        focus_button.click()
        page.wait_for_timeout(500)


def _inspect_brand_hit_target(page: Page, *, label: str) -> None:
    """Assert that the brand resolves to the RouterLink hit target with a pointer cursor."""

    locator = page.locator(".topbar-brand-link")
    box = locator.bounding_box()
    if box is None:
        raise AssertionError(f"{label}: expected the top-bar brand link to be visible.")

    result = page.evaluate(
        """([x, y]) => {
            const element = document.elementFromPoint(x, y);
            if (!element) {
                return null;
            }
            const brandLink = element.closest('a[aria-label="Skriptoteket"]');
            const computedStyle = getComputedStyle(element);
            return {
                tag: element.tagName,
                className: element.className,
                cursor: computedStyle.cursor,
                brandHref: brandLink?.getAttribute('href') ?? null,
            };
        }""",
        [box["x"] + (box["width"] / 2), box["y"] + (box["height"] / 2)],
    )
    if result is None:
        raise AssertionError(f"{label}: expected a visible brand hit target result.")
    assert result["brandHref"] == "/"
    assert result["cursor"] == "pointer"


def main() -> None:
    """Run the top-bar brand hit-target check."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        wait_for_app_heading(page)
        _activate_focus_mode(page)
        _inspect_brand_hit_target(page, label="home")

        page.goto(f"{base_url}/apps/classroom.group-seating-studio", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        _inspect_brand_hit_target(page, label="planner")

        page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
        page.wait_for_timeout(250)
        page.get_by_role("button", name=re.compile(r"Avbryt", re.IGNORECASE)).click()
        page.wait_for_timeout(500)
        _inspect_brand_hit_target(page, label="planner-after-modal-close")

        page.screenshot(
            path=str(ARTIFACTS_DIR / "topbar-brand-hit-target.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
