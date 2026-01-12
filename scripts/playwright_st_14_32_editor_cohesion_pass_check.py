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

    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label(re.compile(r"E-post", re.IGNORECASE)).fill(email)
    dialog.get_by_label(re.compile(r"Lösenord", re.IGNORECASE)).fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
    ).to_be_visible()


def _open_editor(page: object, *, base_url: str) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
    ).to_be_visible()

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    expect(page.locator(".cm-editor").first).to_be_visible(timeout=30_000)


def _screenshot_viewport(page: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=False)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/playwright_st_14_32_editor_cohesion_pass_check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    viewports: list[tuple[int, int]] = [
        (1280, 900),
        (1200, 900),
        (1120, 900),
        (1100, 900),
        (1050, 900),
        (1030, 900),
        (1020, 856),
        (1010, 900),
        (1000, 900),
        (840, 900),
        (756, 1446),
        (749, 900),
        (390, 844),
    ]

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url)

        for width, height in viewports:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(250)
            _screenshot_viewport(page, artifacts_dir / f"responsive-{width}x{height}.png")

            schema_header = page.get_by_text(
                re.compile(r"Indata\s*&\s*inställningar", re.IGNORECASE)
            ).first
            if schema_header.count() > 0:
                schema_header.scroll_into_view_if_needed()
                page.wait_for_timeout(250)
                _screenshot_viewport(page, artifacts_dir / f"schema-{width}x{height}.png")

            settings_schema = page.locator("#tool-settings-schema")
            if settings_schema.count() > 0:
                settings_schema.scroll_into_view_if_needed()
                page.wait_for_timeout(250)
                _screenshot_viewport(page, artifacts_dir / f"schema-settings-{width}x{height}.png")

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
