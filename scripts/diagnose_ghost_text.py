from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config


def _maybe_call(value: object) -> object:
    return value() if callable(value) else value


def _compute_cursor_overlap_chars(prefix: str, completion: str) -> int:
    if not prefix or not completion:
        return 0
    max_len = min(len(prefix), len(completion))
    for size in range(max_len, 0, -1):
        if completion.startswith(prefix[-size:]):
            return size
    return 0


COMPLETION_TIMEOUT_MS = 15_000
COMPLETION_POLL_INTERVAL_MS = 200
GHOST_TIMEOUT_MS = 5_000
CURSOR_SCROLL_WAIT_MS = 200


def _press_doc_end(page: object) -> None:
    page.keyboard.press("Control+End")
    page.keyboard.press("Meta+ArrowDown")


def _press_line_end(page: object) -> None:
    page.keyboard.press("End")
    page.keyboard.press("Meta+ArrowRight")


def _select_line_tail(page: object) -> None:
    page.keyboard.down("Shift")
    page.keyboard.press("End")
    page.keyboard.press("Meta+ArrowRight")
    page.keyboard.up("Shift")


def _select_next_lines(page: object, *, count: int) -> None:
    if count <= 0:
        return
    page.keyboard.down("Shift")
    page.keyboard.press("End")
    page.keyboard.press("Meta+ArrowRight")
    for _ in range(count):
        page.keyboard.press("ArrowDown")
        page.keyboard.press("End")
        page.keyboard.press("Meta+ArrowRight")
    page.keyboard.up("Shift")


def _is_completion_request(request: object) -> bool:
    if not hasattr(request, "url") or not hasattr(request, "method"):
        return False
    return "/api/v1/editor/completions" in request.url and request.method == "POST"


def _fetch_tool_id(
    base_url: str,
    email: str,
    password: str,
    *,
    slug: str | None = None,
) -> str:
    client = httpx.Client(base_url=base_url)
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    tools_response = client.get("/api/v1/admin/tools")
    tools_response.raise_for_status()
    payload = tools_response.json()
    tools = payload.get("tools", []) if isinstance(payload, dict) else []
    if not tools:
        raise RuntimeError("No admin tools available; seed the script bank before running.")
    if slug:
        for tool in tools:
            if isinstance(tool, dict) and tool.get("slug") == slug:
                return tool["id"]
        raise RuntimeError(f"No admin tool found with slug '{slug}'.")
    return tools[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--tool-slug", help="Admin tool slug to target for the editor.", default=None
    )
    parser.add_argument(
        "--cursor-mode",
        choices=["end", "middle"],
        default="end",
        help="Where to place the cursor before typing the stub.",
    )
    parser.add_argument(
        "--cursor-text",
        default="def run_tool",
        help="Text to insert at the cursor before requesting completion.",
    )
    parser.add_argument(
        "--cursor-anchor",
        default=None,
        help="Optional substring to search for before inserting cursor text.",
    )
    parser.add_argument(
        "--cursor-anchor-mode",
        choices=["line", "inline"],
        default="line",
        help=(
            "When using --cursor-anchor, insert on a new line after the anchor line "
            "(line) or inline at the end of the match (inline)."
        ),
    )
    parser.add_argument(
        "--cursor-delete-line-tail",
        action="store_true",
        help="Delete from cursor to end of line after inserting cursor text.",
    )
    parser.add_argument(
        "--cursor-delete-next-lines",
        type=int,
        default=0,
        help="Delete N full lines after the cursor to create a completion hole.",
    )
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0], *remaining]
    config = get_config()
    base_url = config.base_url.rstrip("/")
    artifacts_dir = Path(".artifacts/diagnose-ghost-text")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    tool_id = _fetch_tool_id(
        base_url,
        config.email,
        config.password,
        slug=args.tool_slug or None,
    )
    editor_url = f"{base_url}/admin/tools/{tool_id}"

    result: dict[str, object] = {
        "base_url": base_url,
        "tool_id": tool_id,
        "editor_url": editor_url,
        "cursor_mode": args.cursor_mode,
        "cursor_text": args.cursor_text,
        "cursor_anchor": args.cursor_anchor,
        "cursor_anchor_mode": args.cursor_anchor_mode,
        "cursor_delete_line_tail": args.cursor_delete_line_tail,
        "cursor_delete_next_lines": args.cursor_delete_next_lines,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        completion_request_payload: dict[str, object] | str | None = None
        completion_request_sent = False
        completion_response = None

        def handle_request(request: object) -> None:
            nonlocal completion_request_payload, completion_request_sent
            if not _is_completion_request(request):
                return
            completion_request_sent = True
            if completion_request_payload is not None:
                return
            try:
                completion_request_payload = _maybe_call(request.post_data_json)
            except Exception:
                completion_request_payload = _maybe_call(request.post_data)

        def handle_response(response: object) -> None:
            nonlocal completion_response
            if completion_response is not None:
                return
            if not hasattr(response, "request"):
                return
            if not _is_completion_request(response.request):
                return
            completion_response = response

        page.on("request", handle_request)
        page.on("response", handle_response)

        page.goto(editor_url, wait_until="domcontentloaded")

        # Login modal appears automatically for protected routes.
        expect(page.locator("#login-modal-title")).to_be_visible()
        page.fill("#modal-email", config.email)
        page.fill("#modal-password", config.password)
        page.get_by_role("button", name="Logga in").click()
        page.wait_for_url("**/admin/tools/**")

        # Wait for editor to render.
        expect(page.get_by_text("Källkod")).to_be_visible()
        editor = page.locator('.cm-editor .cm-content[data-language="python"]').first
        expect(editor).to_be_visible()

        content_editable = editor.get_attribute("contenteditable")
        result["contenteditable"] = content_editable

        draft_lock_message = None
        lock_text_locator = page.locator("text=redigeringslås")
        if lock_text_locator.count() > 0:
            draft_lock_message = lock_text_locator.first.text_content()
        if draft_lock_message:
            result["draft_lock_message"] = draft_lock_message.strip()

        # Focus editor and append a marker while preserving context.
        editor.click()
        if args.cursor_anchor:
            page.keyboard.press("Control+F")
            page.keyboard.press("Meta+F")
            page.keyboard.type(args.cursor_anchor)
            page.keyboard.press("Enter")
            page.keyboard.press("Escape")
            if args.cursor_anchor_mode == "inline":
                page.keyboard.press("ArrowRight")
            else:
                _press_line_end(page)
                page.keyboard.press("Enter")
        elif args.cursor_mode == "middle":
            page.evaluate(
                """
                () => {
                  const scroller = document.querySelector('.cm-scroller');
                  if (!scroller) return;
                  scroller.scrollTop = scroller.scrollHeight / 2;
                }
                """
            )
            page.wait_for_timeout(CURSOR_SCROLL_WAIT_MS)
            editor.click()
            _press_line_end(page)
            page.keyboard.press("Enter")
        else:
            _press_doc_end(page)
            page.keyboard.press("Enter")
        page.keyboard.type(args.cursor_text)
        if args.cursor_delete_line_tail:
            _select_line_tail(page)
            page.keyboard.press("Backspace")
        if args.cursor_delete_next_lines > 0:
            _select_next_lines(page, count=args.cursor_delete_next_lines)
            page.keyboard.press("Backspace")
        result["typed_snippet"] = args.cursor_text

        completion_payload = None
        # Manual trigger (Alt-\\).
        page.keyboard.press("Alt+Backslash")
        deadline = time.monotonic() + (COMPLETION_TIMEOUT_MS / 1000)
        while completion_response is None and time.monotonic() < deadline:
            page.wait_for_timeout(COMPLETION_POLL_INTERVAL_MS)

        if completion_response is None:
            result["completion_request"] = "timeout" if completion_request_sent else "not_sent"
        else:
            completion_payload = _maybe_call(completion_response.json)
            if completion_request_payload is None:
                try:
                    completion_request_payload = _maybe_call(
                        completion_response.request.post_data_json
                    )
                except Exception:
                    completion_request_payload = _maybe_call(completion_response.request.post_data)

        if completion_request_payload is not None:
            result["completion_request_payload"] = completion_request_payload
        if completion_response is not None:
            result["completion_request"] = "sent"
            result["completion_status"] = completion_response.status
            result["completion_payload"] = completion_payload
            if (
                isinstance(completion_payload, dict)
                and isinstance(completion_request_payload, dict)
                and isinstance(completion_payload.get("completion"), str)
                and isinstance(completion_request_payload.get("prefix"), str)
            ):
                result["cursor_overlap_chars"] = _compute_cursor_overlap_chars(
                    completion_request_payload["prefix"],
                    completion_payload["completion"],
                )

        ghost = page.locator(".cm-skriptoteket-ghost-text")
        try:
            ghost.first.wait_for(state="visible", timeout=GHOST_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass
        result["ghost_text_present"] = ghost.count() > 0
        if ghost.count() > 0:
            result["ghost_text"] = ghost.first.text_content()

        # Undo any edits to avoid saving modifications.
        page.keyboard.press("Control+Z")
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
