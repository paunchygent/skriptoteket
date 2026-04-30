from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import (
    create_signed_huleedu_api_session,
    install_local_huleedu_auth_routes,
)

EDIT_OPS_TIMEOUT_MS = 180_000
EDIT_OPS_POLL_INTERVAL_MS = 250

CURSOR_SCROLL_WAIT_MS = 200


def _maybe_call(value: object) -> object:
    return value() if callable(value) else value


def _frontend_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if port == 8000 or port is None:
        port = 5173
    netloc = f"{host}:{port}"
    return urlunparse(parsed._replace(netloc=netloc))


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


def _is_edit_ops_request(request: object) -> bool:
    if not hasattr(request, "url") or not hasattr(request, "method"):
        return False
    return "/api/v1/editor/edit-ops" in request.url and request.method == "POST"


def _is_edit_ops_preview_request(request: object) -> bool:
    if not hasattr(request, "url") or not hasattr(request, "method"):
        return False
    return "/api/v1/editor/edit-ops/preview" in request.url and request.method == "POST"


def _fetch_tool_id(base_url: str, signed_headers: dict[str, str], *, slug: str) -> str:
    client = httpx.Client(base_url=base_url.rstrip("/"), headers=signed_headers)
    tools_response = client.get("/api/v1/admin/tools")
    tools_response.raise_for_status()
    payload = tools_response.json()
    tools = payload.get("tools", []) if isinstance(payload, dict) else []
    if not tools:
        raise RuntimeError(
            "No admin tools available; seed the script bank before running "
            "(example: pdm run seed-script-bank --slug html-to-pdf-preview)."
        )
    for tool in tools:
        if isinstance(tool, dict) and tool.get("slug") == slug:
            return tool["id"]
    raise RuntimeError(
        f"No admin tool found with slug '{slug}'. Seed it via "
        f"pdm run seed-script-bank --slug {slug}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--tool-slug",
        help="Admin tool slug to target for the editor.",
        default="html-to-pdf-preview",
    )
    parser.add_argument(
        "--edit-message",
        default=(
            "Fyll i den saknade koden vid markören. Behåll resten oförändrat. "
            "Om du ser ett ofullständigt `return {`, komplettera det till en giltig "
            "return-dict med outputs/next_actions/state enligt kontraktet."
        ),
        help="The user instruction sent to edit-ops (the 'Edit' tab).",
    )
    parser.add_argument(
        "--cursor-mode",
        choices=["end", "middle"],
        default="end",
        help="Where to place the cursor before typing the stub.",
    )
    parser.add_argument(
        "--cursor-text",
        default="return {",
        help="Text to insert at the cursor before requesting edit-ops.",
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
        help="Delete N full lines after the cursor to create a realistic edit hole.",
    )
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0], *remaining]
    config = get_config()
    api_url = config.base_url.rstrip("/")
    app_url = _frontend_url(api_url)

    artifacts_dir = Path(".artifacts/diagnose-edit-ops")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    auth = create_signed_huleedu_api_session(
        email=config.email,
        display_name="Edit Ops Diagnostic Teacher",
        role="superuser",
        jti=f"diagnose-edit-ops-{int(time.time())}",
    )
    tool_id = _fetch_tool_id(api_url, auth.signed_headers, slug=args.tool_slug)
    editor_url = f"{app_url}/admin/tools/{tool_id}"

    result: dict[str, object] = {
        "api_url": api_url,
        "app_url": app_url,
        "tool_id": tool_id,
        "editor_url": editor_url,
        "tool_slug": args.tool_slug,
        "edit_message": args.edit_message,
        "cursor_mode": args.cursor_mode,
        "cursor_text": args.cursor_text,
        "cursor_anchor": args.cursor_anchor,
        "cursor_anchor_mode": args.cursor_anchor_mode,
        "cursor_delete_line_tail": args.cursor_delete_line_tail,
        "cursor_delete_next_lines": args.cursor_delete_next_lines,
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        edit_ops_request_payload: dict[str, object] | str | None = None
        edit_ops_request_headers: dict[str, str] | None = None
        edit_ops_response = None

        preview_request_payload: dict[str, object] | str | None = None
        preview_request_headers: dict[str, str] | None = None
        preview_response = None

        def handle_request(request: object) -> None:
            nonlocal edit_ops_request_payload
            nonlocal edit_ops_request_headers
            nonlocal preview_request_payload
            nonlocal preview_request_headers

            if _is_edit_ops_request(request):
                if edit_ops_request_headers is None:
                    edit_ops_request_headers = dict(getattr(request, "headers", {}) or {})
                if edit_ops_request_payload is None:
                    try:
                        edit_ops_request_payload = _maybe_call(request.post_data_json)
                    except Exception:
                        edit_ops_request_payload = _maybe_call(request.post_data)
                return

            if _is_edit_ops_preview_request(request):
                if preview_request_headers is None:
                    preview_request_headers = dict(getattr(request, "headers", {}) or {})
                if preview_request_payload is None:
                    try:
                        preview_request_payload = _maybe_call(request.post_data_json)
                    except Exception:
                        preview_request_payload = _maybe_call(request.post_data)

        def handle_response(response: object) -> None:
            nonlocal edit_ops_response
            nonlocal preview_response

            if not hasattr(response, "request"):
                return
            request = response.request

            if edit_ops_response is None and _is_edit_ops_request(request):
                edit_ops_response = response
                return
            if preview_response is None and _is_edit_ops_preview_request(request):
                preview_response = response

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            install_local_huleedu_auth_routes(
                page,
                base_url=app_url,
                signed_headers=auth.signed_headers,
                provider_subject=auth.provider_subject,
                provider_email=auth.provider_email,
                display_name=auth.display_name,
            )

            page.goto(editor_url, wait_until="domcontentloaded")

            expect(page.get_by_text("Källkod")).to_be_visible()
            editor = page.locator('.cm-editor .cm-content[data-language="python"]').first
            expect(editor).to_be_visible()

            editor.click()
            page.keyboard.press("Escape")

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

            drawer = page.get_by_role("dialog", name=re.compile(r"Kodassistenten", re.IGNORECASE))
            expect(drawer).to_be_visible()

            toggle = drawer.get_by_role(
                "button",
                name=re.compile(r"(Minimera|Expandera) kodassistenten", re.IGNORECASE),
            )
            chat_body = drawer.locator(".chat-body")
            if toggle.count() > 0 and chat_body.count() > 0:
                if chat_body.get_attribute("aria-hidden") == "true":
                    toggle.click()
                    expect(chat_body).not_to_have_attribute("aria-hidden", "true")

            submit = None
            edit_tab = drawer.get_by_role("tab", name=re.compile(r"Edit", re.IGNORECASE))
            if edit_tab.count() > 0:
                edit_tab.first.click()
                textarea = drawer.get_by_placeholder(
                    re.compile(r"Beskriv vad du vill ändra", re.IGNORECASE)
                )
                expect(textarea).to_be_visible()
                textarea.fill(args.edit_message)
                submit = drawer.get_by_label(re.compile(r"Föreslå ändringar", re.IGNORECASE))
            else:
                message_input = drawer.get_by_placeholder(
                    re.compile(r"Beskriv ditt m.l", re.IGNORECASE)
                )
                expect(message_input).to_be_visible()
                message_input.fill(args.edit_message)
                submit = drawer.get_by_role(
                    "button", name=re.compile(r"F.resl. .*ndringar", re.IGNORECASE)
                )

            expect(submit).to_be_enabled()
            submit.click()
        except Exception:
            page.screenshot(path=str(artifacts_dir / "failure.png"), full_page=True)
            raise

        deadline = time.monotonic() + (EDIT_OPS_TIMEOUT_MS / 1000)
        while (
            edit_ops_response is None or preview_response is None
        ) and time.monotonic() < deadline:
            page.wait_for_timeout(EDIT_OPS_POLL_INTERVAL_MS)

        result["edit_ops_request_headers"] = edit_ops_request_headers
        result["edit_ops_request_payload"] = edit_ops_request_payload
        result["preview_request_headers"] = preview_request_headers
        result["preview_request_payload"] = preview_request_payload

        if edit_ops_request_headers:
            result["correlation_id"] = edit_ops_request_headers.get("x-correlation-id")

        if edit_ops_response is not None:
            result["edit_ops_status"] = edit_ops_response.status
            try:
                result["edit_ops_response"] = _maybe_call(edit_ops_response.json)
            except Exception as exc:
                result["edit_ops_response_error"] = type(exc).__name__

        if preview_response is not None:
            result["preview_status"] = preview_response.status
            try:
                result["preview_response"] = _maybe_call(preview_response.json)
            except Exception as exc:
                result["preview_response_error"] = type(exc).__name__

        error_text = None
        error_banner = drawer.get_by_text(
            re.compile(r"Patchen kunde inte appliceras", re.IGNORECASE)
        )
        if error_banner.count() > 0 and error_banner.first.is_visible():
            error_text = error_banner.first.text_content()
        result["ui_error_banner"] = error_text.strip() if isinstance(error_text, str) else None

        try:
            expect(page.get_by_text(re.compile(r"AI-förslag", re.IGNORECASE))).to_be_visible(
                timeout=10_000
            )
        except (AssertionError, PlaywrightTimeoutError):
            pass

        page.screenshot(path=str(artifacts_dir / "editor.png"), full_page=True)
        (artifacts_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # Undo local edits (cursor text + deletions) to avoid persisting modifications.
        for _ in range(12):
            page.keyboard.press("Control+Z")

        browser.close()

    print(f"Wrote artifacts to {artifacts_dir}")


if __name__ == "__main__":
    main()
