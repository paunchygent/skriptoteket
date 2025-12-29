from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium, _login


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/ui-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        _login(page, base_url=base_url, email=config.email, password=config.password)

        page.goto(f"{base_url}/suggestions/new", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Föreslå ett nytt verktyg", re.IGNORECASE))
        ).to_be_visible()

        expect(page.locator("#description")).to_be_visible()

        help_btn = page.get_by_role("button", name=re.compile(r"Visa hjälp", re.IGNORECASE))
        expect(help_btn).to_be_visible()
        help_btn.click()

        note = page.locator("#suggestion-description-help")
        expect(note).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "suggestion-new-help.png"), full_page=True)

        note.get_by_role("button", name=re.compile(r"Stäng hjälp", re.IGNORECASE)).click()
        expect(note).to_be_hidden()
        page.screenshot(path=str(artifacts_dir / "suggestion-new-help-closed.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Suggestion help screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
