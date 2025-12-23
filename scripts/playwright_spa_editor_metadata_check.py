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


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/spa-editor-metadata-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Login (SPA)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible()

        # Pick any tool from the admin list
        tools_response = context.request.get(f"{base_url}/api/v1/admin/tools")
        expect(tools_response).to_be_ok()
        tools_payload = tools_response.json()
        tools = tools_payload.get("tools", [])
        assert tools, "Expected at least one admin tool to exist for metadata editor check."

        tool_id = tools[0].get("id")
        assert tool_id, "Expected tool id in admin tools payload."

        page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Källkod", re.IGNORECASE))
        ).to_be_visible()
        expect(
            page.get_by_role("heading", name=re.compile(r"Metadata", re.IGNORECASE))
        ).to_be_visible()

        title_input = page.locator("input[placeholder='Titel']")
        summary_input = page.locator("textarea[placeholder='Valfri sammanfattning']")
        save_button = page.get_by_role("button", name=re.compile(r"Spara metadata", re.IGNORECASE))

        expect(title_input).to_be_visible()
        expect(summary_input).to_be_visible()
        expect(save_button).to_be_visible()

        original_title = title_input.input_value()
        original_summary = summary_input.input_value()

        # Validation: title required (client-side check)
        title_input.fill("")
        save_button.click()
        expect(page.get_by_text("Titel krävs.")).to_be_visible()

        # Save metadata changes and verify they persist after reload.
        updated_title = f"{original_title} (meta check)"
        updated_summary = original_summary
        if updated_summary:
            updated_summary = f"{updated_summary} (meta check)"
        else:
            updated_summary = "meta check"

        title_input.fill(updated_title)
        summary_input.fill(updated_summary)
        save_button.click()
        expect(page.get_by_text("Metadata sparad.")).to_be_visible()

        expect(
            page.get_by_role("heading", name=re.compile(re.escape(updated_title)))
        ).to_be_visible()

        page.reload(wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Metadata", re.IGNORECASE))
        ).to_be_visible()
        expect(title_input).to_have_value(updated_title)
        expect(summary_input).to_have_value(updated_summary)

        page.screenshot(path=str(artifacts_dir / "editor-metadata-updated.png"), full_page=True)

        # Restore original values to keep local dev data stable.
        title_input.fill(original_title)
        summary_input.fill(original_summary)
        save_button.click()
        expect(page.get_by_text("Metadata sparad.")).to_be_visible()

        page.screenshot(path=str(artifacts_dir / "editor-metadata-restored.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
