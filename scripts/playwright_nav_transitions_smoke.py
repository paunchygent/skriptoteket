from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium


def _login_with_next(
    page: object, *, base_url: str, email: str, password: str, next_path: str
) -> None:
    next_param = urllib.parse.quote(next_path, safe="/")
    page.goto(f"{base_url}/login?next={next_param}", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page).to_have_url(
        re.compile(re.escape(base_url) + re.escape(next_path) + r"(/)?$"), timeout=15_000
    )
    expect(
        page.get_by_role("heading", name=re.compile(r"Mina (körningar|verktyg)", re.IGNORECASE))
    ).to_be_visible(timeout=15_000)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/ui-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        _login_with_next(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
            next_path="/my-runs",
        )

        sidebar = page.locator("aside.sidebar")
        expect(sidebar).to_be_visible()

        # Login redirect target (captures redirect-specific transition behavior)
        expect(
            page.get_by_role("heading", name=re.compile(r"Mina körningar", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-redirect-my-runs.png"), full_page=True)

        # Navigate via RouterLink (SPA transition)
        sidebar.get_by_role("link", name=re.compile(r"Hem", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-home.png"), full_page=True)

        sidebar.get_by_role("link", name=re.compile(r"Katalog", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Katalog", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-browse.png"), full_page=True)

        sidebar.get_by_role("link", name=re.compile(r"Föreslå verktyg", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Föreslå ett nytt verktyg", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-suggestion-new.png"), full_page=True)

        sidebar.get_by_role("link", name=re.compile(r"Mina verktyg", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Mina verktyg", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-my-tools.png"), full_page=True)

        sidebar.get_by_role("link", name=re.compile(r"Profil", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Profil", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-profile.png"), full_page=True)

        # Navigate to /my-runs from another view (captures any "shutter" artifacts during transition)
        sidebar.get_by_role("link", name=re.compile(r"Mina körningar", re.IGNORECASE)).click()
        page.wait_for_timeout(50)
        page.screenshot(path=str(artifacts_dir / "nav-my-runs-t+050ms.png"), full_page=True)
        page.wait_for_timeout(100)
        page.screenshot(path=str(artifacts_dir / "nav-my-runs-t+150ms.png"), full_page=True)
        expect(
            page.get_by_role("heading", name=re.compile(r"Mina körningar", re.IGNORECASE))
        ).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "nav-my-runs.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Navigation transition screenshots written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
