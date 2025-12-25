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
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()

    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def main() -> None:
    """Test personalized tool settings using dedicated demo-settings-test tool.

    Uses demo-settings-test (pre-seeded with settings_schema) to avoid polluting demo-next-actions.
    """
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-12-03-personalized-tool-settings-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hej!\nST-12-03 personalized settings e2e.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)

        # Use dedicated demo-settings-test tool (pre-seeded with settings_schema)
        tool_slug = "demo-settings-test"
        page.goto(f"{base_url}/tools/{tool_slug}/run", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Demo: Personalized", re.IGNORECASE))
        ).to_be_visible()

        # Open settings panel and configure theme_color
        settings_toggle = page.get_by_role(
            "button", name=re.compile(r"Inställningar", re.IGNORECASE)
        ).first
        expect(settings_toggle).to_be_visible(timeout=20_000)
        settings_toggle.click()

        theme_field = page.get_by_label("Färgtema").first
        expect(theme_field).to_be_visible()
        theme_field.fill("#ff00ff")

        save_settings = page.get_by_role("button", name=re.compile(r"^Spara$", re.IGNORECASE)).first
        save_settings.click()
        expect(page.get_by_text("Inställningar sparade.")).to_be_visible(timeout=20_000)
        page.screenshot(path=str(artifacts_dir / "settings-saved.png"), full_page=True)

        # Run tool and verify settings are injected
        page.locator("input[type='file']").set_input_files(str(sample_file))
        page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()

        expect(page.get_by_text("theme_color=#ff00ff")).to_be_visible(timeout=60_000)
        page.screenshot(path=str(artifacts_dir / "run-with-settings.png"), full_page=True)

        # Verify settings persistence after page reload
        page.reload(wait_until="domcontentloaded")
        settings_toggle = page.get_by_role(
            "button", name=re.compile(r"Inställningar", re.IGNORECASE)
        ).first
        settings_toggle.click()
        expect(page.get_by_label("Färgtema").first).to_have_value("#ff00ff")
        page.screenshot(path=str(artifacts_dir / "settings-persisted.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
