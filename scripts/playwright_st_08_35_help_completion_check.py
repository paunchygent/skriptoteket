"""Live Playwright proof for ST-08-35 help completion behavior.

This targeted check exercises the public help drawer path, keyboard/backdrop
close behavior, opener focus restoration, route resync while the drawer remains
open, calm help-index styling, and public Klassrumskartan blocked-state CTA
geometry. It intentionally avoids authenticated-only checks.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_browser import launch_chromium

PUBLIC_CLASSROOM_PATH = "/public/apps/classroom.group-seating-studio"
GUEST_AUTHORING_CLOSED_KEY = "skriptoteket:classroom-planner:guest-authoring-closed"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ST-08-35 public help drawer live proof",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Frontend base URL (default: http://127.0.0.1:5173)",
    )
    return parser.parse_args()


def _assert_same_size(left: dict[str, float], right: dict[str, float]) -> None:
    if round(left["width"]) != round(right["width"]) or round(left["height"]) != round(
        right["height"]
    ):
        raise AssertionError(f"CTA geometry mismatch: login={left}, register={right}")


def main() -> None:
    args = _parse_args()
    base_url = args.base_url.rstrip("/")
    artifacts_dir = Path(".artifacts/st-08-35-help-completion-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 820})
        page = context.new_page()

        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        help_button = page.get_by_role("button", name=re.compile(r"^Hjälp$", re.IGNORECASE))
        expect(help_button).to_be_visible()
        help_button.click()

        help_panel = page.locator("#help-panel")
        expect(page.get_by_role("heading", name="Hjälp", exact=True)).to_be_visible()
        expect(help_panel.get_by_text("Hjälpindex")).to_be_visible()
        expect(help_panel.get_by_text("Logga in", exact=True)).to_be_visible()
        expect(help_panel.get_by_text("Konto och lösenord", exact=True)).to_be_visible()
        expect(help_panel.get_by_text("Start samlar")).to_be_hidden()

        panel_background = page.locator(".help-panel").evaluate(
            "element => getComputedStyle(element).backgroundColor"
        )
        if panel_background in {"transparent", "rgba(0, 0, 0, 0)"}:
            raise AssertionError(f"Unexpected help panel background: {panel_background}")

        list_shadows = page.locator('[data-test="help-index-list"]').evaluate_all(
            "elements => elements.map((element) => getComputedStyle(element).boxShadow)"
        )
        if any(shadow != "none" for shadow in list_shadows):
            raise AssertionError(f"Help-index lists should not cast shadows: {list_shadows}")

        page.screenshot(path=str(artifacts_dir / "public-help-index.png"), full_page=True)

        page.keyboard.press("Escape")
        expect(page.locator("#help-panel")).to_be_hidden()
        expect(help_button).to_be_focused()

        help_button.click()
        expect(page.locator("#help-panel")).to_be_visible()
        page.locator(".help-backdrop").click(position={"x": 4, "y": 4})
        expect(page.locator("#help-panel")).to_be_hidden()
        expect(help_button).to_be_focused()

        help_button.click()
        expect(page.locator("#help-panel")).to_be_visible()
        page.locator(f'a[href="{PUBLIC_CLASSROOM_PATH}"]').first.evaluate(
            "element => element.click()"
        )
        page.wait_for_url(re.compile(rf"{re.escape(PUBLIC_CLASSROOM_PATH)}(?:$|\?)"))
        expect(
            page.get_by_text("Detta är en fullständig förhandsvisning av vad Klassrumskartan gör.")
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "public-app-help-resynced.png"), full_page=True)

        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        page.evaluate(f"window.localStorage.setItem('{GUEST_AUTHORING_CLOSED_KEY}', 'true')")
        page.goto(f"{base_url}{PUBLIC_CLASSROOM_PATH}", wait_until="domcontentloaded")
        expect(page.get_by_text("Logga in för att fortsätta")).to_be_visible()

        login_box = page.locator('[data-test="public-guest-authoring-closed-login"]').bounding_box()
        register_box = page.locator(
            '[data-test="public-guest-authoring-closed-register"]'
        ).bounding_box()
        if login_box is None or register_box is None:
            raise AssertionError("Could not read blocked-state CTA geometry.")
        _assert_same_size(login_box, register_box)
        page.screenshot(
            path=str(artifacts_dir / "public-classroom-blocked-ctas.png"), full_page=True
        )

        context.close()
        browser.close()

    print(f"ST-08-35 help completion artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
