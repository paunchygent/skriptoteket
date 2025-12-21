from __future__ import annotations

import re
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def main() -> None:
    config = get_config()
    base_url = config.base_url
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-editor-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    marker = uuid.uuid4().hex[:8]
    new_source_code = (
        "def run_tool(input_path: str, output_dir: str) -> str:\n"
        '    return "<p>ok</p>"\n'
        f"# playwright-marker:{marker}\n"
    )

    with sync_playwright() as playwright:
        browser = playwright.webkit.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Login (bootstrap account from .env)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name="Logga in").click()
        expect(page.get_by_text("Inloggad som")).to_be_visible()

        # Navigate to first tool editor page
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        edit_link = page.get_by_role("link", name="Redigera").first
        if edit_link.count() == 0:
            raise RuntimeError("No tools found in /admin/tools; cannot smoke-test the editor page.")

        edit_link.click()
        page.wait_for_load_state("domcontentloaded")

        # Ensure SPA island mounts (CodeMirror 6)
        expect(page.locator("#spa-editor-main-target .cm-editor")).to_be_visible()

        # Regression check: navigate away and back without a full reload (hx-boost).
        # The editor island must mount again even though the Vite module won't re-execute.
        page.get_by_role("link", name="Testyta").click()
        page.wait_for_url("**/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        edit_link = page.get_by_role("link", name="Redigera").first
        if edit_link.count() == 0:
            raise RuntimeError("No tools found in /admin/tools; cannot re-open the editor page.")

        edit_link.click()
        expect(page.locator("#spa-editor-main-target .cm-editor")).to_be_visible()

        # Replace editor contents and save (create draft OR save snapshot)
        page.locator("#spa-editor-main-target .cm-content").click()
        page.keyboard.press("Meta+A")
        page.keyboard.type(new_source_code)

        save_button = page.locator("#spa-editor-sidebar-target button").first
        expect(save_button).to_be_visible()
        save_button.click()

        page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")
        expect(page.locator("#toast-container .huleedu-toast")).to_contain_text(
            re.compile(r"(Utkast skapat\.|Sparat\.)")
        )

        # Ensure the new server-rendered payload contains the marker (persisted)
        payload_text = page.locator("#spa-island-editor-payload").text_content() or ""
        assert marker in payload_text, "Saved payload did not include the expected marker."

        # Ensure island mounts after redirect, too.
        expect(page.locator("#spa-editor-main-target .cm-editor")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "editor.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright editor smoke screenshot written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
