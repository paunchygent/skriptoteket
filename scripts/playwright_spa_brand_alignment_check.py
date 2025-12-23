from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config

HULEEDU_WARNING_BORDER = "rgb(217, 119, 6)"


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

    artifacts_dir = Path(".artifacts/spa-brand-alignment-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Logged out: capture landing header brand x
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        landing_brand = page.locator("header .landing-brand")
        expect(landing_brand).to_be_visible()
        landing_box = landing_brand.bounding_box()
        assert landing_box is not None, "Expected landing brand to have a bounding box"

        # Hover state: navy CTA should highlight amber (same as outline buttons).
        login_cta = page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE))
        if login_cta.count() > 0:
            login_cta.first.hover()
            expect(login_cta.first).to_have_css("border-top-color", HULEEDU_WARNING_BORDER)

        page.screenshot(path=str(artifacts_dir / "landing-logged-out.png"), full_page=True)

        # Login (SPA)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible()
        sidebar_brand = page.locator(".sidebar-brand")
        expect(sidebar_brand).to_be_visible()
        sidebar_box = sidebar_brand.bounding_box()
        assert sidebar_box is not None, "Expected sidebar brand to have a bounding box"
        page.screenshot(path=str(artifacts_dir / "dashboard-logged-in.png"), full_page=True)

        landing_x = round(landing_box["x"], 1)
        sidebar_x = round(sidebar_box["x"], 1)
        diff = abs(landing_x - sidebar_x)

        (artifacts_dir / "positions.txt").write_text(
            f"landing_x={landing_x}\nsidebar_x={sidebar_x}\ndiff={diff}\n", encoding="utf-8"
        )

        assert diff <= 1.0, (
            "Expected landing header brand and authenticated sidebar brand to align closely. "
            f"Got diff={diff} (landing_x={landing_x}, sidebar_x={sidebar_x})."
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
