from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import Route, expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_st_08_14_ai_inline_completions_e2e import (
    _clear_codemirror,
    _launch_chromium,
    _login,
    _open_editor,
    _wait_for_intelligence_loaded,
)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-08-16-ai-edit-suggestions-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    suggestion_payload = "return 2\n"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def handle_edits(route: Route) -> None:
            request = route.request
            csrf = request.headers.get("x-csrf-token")
            if not csrf:
                raise AssertionError("Expected X-CSRF-Token header on /edits request")

            payload = json.loads(request.post_data or "{}")
            assert "selection" in payload and payload["selection"].strip()
            assert "prefix" in payload and "suffix" in payload

            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"suggestion": suggestion_payload, "enabled": True}),
            )

        page.route("**/api/v1/editor/edits", handle_edits)

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _wait_for_intelligence_loaded(page)

        _clear_codemirror(page)
        page.keyboard.type("def run_tool(input_dir, output_dir):\n    return 1")

        # Select "return 1" using keyboard selection from line end.
        page.keyboard.down("Shift")
        for _ in range(len("return 1")):
            page.keyboard.press("ArrowLeft")
        page.keyboard.up("Shift")

        request_button = page.get_by_role(
            "button", name=re.compile(r"Föreslå ändring", re.IGNORECASE)
        )
        request_button.click()

        suggestion_area = page.get_by_label("Förslag")
        expect(suggestion_area).to_have_value(re.compile(r"return 2", re.IGNORECASE))
        page.screenshot(path=str(artifacts_dir / "edit-suggestion-preview.png"), full_page=True)

        apply_button = page.get_by_role("button", name=re.compile(r"Använd förslag", re.IGNORECASE))
        apply_button.click()

        content = page.locator(".cm-editor .cm-content").first
        expect(content).to_contain_text("return 2")
        page.screenshot(path=str(artifacts_dir / "edit-suggestion-applied.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
