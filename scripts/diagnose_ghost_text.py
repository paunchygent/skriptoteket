from __future__ import annotations

import json
from pathlib import Path

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def _maybe_call(value: object) -> object:
    return value() if callable(value) else value


def _fetch_first_tool_id(base_url: str, email: str, password: str) -> str:
    client = httpx.Client(base_url=base_url)
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    tools_response = client.get("/api/v1/admin/tools")
    tools_response.raise_for_status()
    payload = tools_response.json()
    tools = payload.get("tools", []) if isinstance(payload, dict) else []
    if not tools:
        raise RuntimeError("No admin tools available; seed the script bank before running.")
    return tools[0]["id"]


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    artifacts_dir = Path(".artifacts/diagnose-ghost-text")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    tool_id = _fetch_first_tool_id(base_url, config.email, config.password)
    editor_url = f"{base_url}/admin/tools/{tool_id}"

    result: dict[str, object] = {
        "base_url": base_url,
        "tool_id": tool_id,
        "editor_url": editor_url,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        completion_request_payload: dict[str, object] | str | None = None

        def handle_request(request: object) -> None:
            nonlocal completion_request_payload
            req = request  # type: ignore[assignment]
            if "/api/v1/editor/completions" not in req.url or req.method != "POST":
                return
            try:
                completion_request_payload = _maybe_call(req.post_data_json)
            except Exception:
                completion_request_payload = _maybe_call(req.post_data)

        page.on("request", handle_request)

        page.goto(editor_url, wait_until="domcontentloaded")

        # Login modal appears automatically for protected routes.
        expect(page.locator("#login-modal-title")).to_be_visible()
        page.fill("#modal-email", config.email)
        page.fill("#modal-password", config.password)
        page.get_by_role("button", name="Logga in").click()
        page.wait_for_url("**/admin/tools/**")

        # Wait for editor to render.
        expect(page.get_by_text("Källkod")).to_be_visible()
        editor = page.locator(".cm-editor .cm-content")
        expect(editor).to_be_visible()

        content_editable = editor.get_attribute("contenteditable")
        result["contenteditable"] = content_editable

        draft_lock_message = None
        lock_text_locator = page.locator("text=redigeringslås")
        if lock_text_locator.count() > 0:
            draft_lock_message = lock_text_locator.first.text_content()
        if draft_lock_message:
            result["draft_lock_message"] = draft_lock_message.strip()

        # Focus editor and place cursor inside run_tool for a non-trivial inline request.
        editor.click()
        run_tool_line = page.locator("text=def run_tool")
        if run_tool_line.count() > 0:
            run_tool_line.first.click()
            page.keyboard.press("End")
            page.keyboard.press("Enter")
            page.keyboard.type("    print(")
            result["typed_snippet"] = "print("

        # Manual trigger (Alt-\\).
        page.keyboard.press("Alt+Backslash")

        completion_response = None
        completion_payload = None
        try:
            with page.expect_response(
                lambda resp: "/api/v1/editor/completions" in resp.url
                and resp.request.method == "POST",
                timeout=5000,
            ) as response_info:
                pass
            completion_response = response_info.value
            completion_payload = _maybe_call(completion_response.json)
        except PlaywrightTimeoutError:
            result["completion_request"] = "not_sent"

        if completion_request_payload is not None:
            result["completion_request_payload"] = completion_request_payload
        if completion_response is not None:
            result["completion_request"] = "sent"
            result["completion_status"] = completion_response.status
            result["completion_payload"] = completion_payload

        ghost = page.locator(".cm-skriptoteket-ghost-text")
        result["ghost_text_present"] = ghost.count() > 0
        if ghost.count() > 0:
            result["ghost_text"] = ghost.first.text_content()

        # Undo any edits to avoid saving modifications.
        page.keyboard.press("Control+Z")
        page.keyboard.press("Control+Z")

        page.screenshot(path=str(artifacts_dir / "editor.png"), full_page=True)
        (artifacts_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        browser.close()

    print(f"Wrote artifacts to {artifacts_dir}")


if __name__ == "__main__":
    main()
