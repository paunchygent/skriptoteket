from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/ui-edit-ops-diff-scroll")


def _maybe_call(value: object) -> object:
    return value() if callable(value) else value


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
        return playwright.chromium.launch(headless=True, channel="chrome")
    except PlaywrightError:
        pass

    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as exc:
        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise exc

        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _frontend_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if port == 8000 or port is None:
        port = 5173
    netloc = f"{host}:{port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")

    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label(re.compile(r"E-post", re.IGNORECASE)).fill(email)
    dialog.get_by_label(re.compile(r"L.senord", re.IGNORECASE)).fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"V.lkommen", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        page.screenshot(path=str(ARTIFACTS_DIR / "login-failure.png"), full_page=True)
        raise


def _open_first_tool_editor(page: object, *, base_url: str) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        page.screenshot(path=str(ARTIFACTS_DIR / "open-tools-failure.png"), full_page=True)
        raise

    empty_state = page.get_by_text("Inga verktyg finns.")
    if empty_state.count() > 0 and empty_state.is_visible():
        raise RuntimeError("No tools available to verify edit-ops diff scroll.")

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        mode_button = page.get_by_role("button", name=re.compile(r"K.llkod", re.IGNORECASE))
        expect(mode_button).to_be_visible()
    except AssertionError:
        page.screenshot(path=str(ARTIFACTS_DIR / "open-editor-failure.png"), full_page=True)
        raise


def _stub_edit_ops(page: object) -> None:
    def handle_edit_ops(route, request):
        payload = _maybe_call(request.post_data_json) or {}
        base_files = payload.get("virtual_files", {}) if isinstance(payload, dict) else {}
        response = {
            "enabled": True,
            "assistant_message": "Jag har föreslagit en större förändring.",
            "base_fingerprints": {key: f"sha256:{value}" for key, value in base_files.items()},
            "ops": [
                {
                    "op": "patch",
                    "target_file": "tool.py",
                    "patch_lines": [
                        "--- a/tool.py",
                        "+++ b/tool.py",
                        "@@ -1,1 +1,6 @@",
                        "-print('hej')",
                        "+print('hej')",
                        "+# extra rad 1",
                        "+# extra rad 2",
                        "+# extra rad 3",
                        "+# extra rad 4",
                        "+# extra rad 5",
                    ],
                }
            ],
        }
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(response, ensure_ascii=False),
        )

    def handle_preview(route, request):
        payload = _maybe_call(request.post_data_json) or {}
        virtual_files = payload.get("virtual_files", {}) if isinstance(payload, dict) else {}
        tool_body = virtual_files.get("tool.py", "") if isinstance(virtual_files, dict) else ""
        filler = "\n".join([f"# filler {idx}" for idx in range(1, 220)])
        after_tool = f"{tool_body}\n# preview change\n{filler}\n"
        after_virtual_files = dict(virtual_files) if isinstance(virtual_files, dict) else {}
        after_virtual_files["tool.py"] = after_tool
        response = {
            "ok": True,
            "after_virtual_files": after_virtual_files,
            "errors": [],
            "error_details": [],
            "meta": {
                "base_hash": "sha256:base",
                "patch_id": "sha256:patch",
                "requires_confirmation": True,
                "fuzz_level_used": 1,
                "max_offset": 21,
                "normalizations_applied": [
                    "trimmed_blank_lines",
                    "added_trailing_newline",
                    "synthesized_file_headers",
                ],
                "applied_cleanly": False,
            },
        }
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(response, ensure_ascii=False),
        )

    page.route("**/api/v1/editor/edit-ops", handle_edit_ops)
    page.route("**/api/v1/editor/edit-ops/preview", handle_preview)


def _request_edit_ops(page: object) -> None:
    drawer = page.get_by_role("dialog", name=re.compile(r"Kodassistenten", re.IGNORECASE))
    expect(drawer).to_be_visible()

    edit_tab = drawer.get_by_role("tab", name="Edit", exact=True)
    expect(edit_tab).to_be_visible()
    edit_tab.click()

    textarea = drawer.get_by_placeholder(re.compile(r"Beskriv vad du vill ändra", re.IGNORECASE))
    expect(textarea).to_be_visible()
    textarea.fill("Gör en stor uppdatering av koden.")

    submit = drawer.get_by_label(re.compile(r"Föreslå ändringar", re.IGNORECASE))
    expect(submit).to_be_enabled()
    submit.click()


def _assert_panel_scroll(page: object) -> None:
    panel = page.locator('[data-editor-panel="mode"]').first
    expect(panel).to_be_visible()

    panel_state = panel.evaluate(
        """(el) => {
        const style = window.getComputedStyle(el);
        const beforeTop = el.scrollTop;
        const canScroll = el.scrollHeight > el.clientHeight;
        el.scrollTop = beforeTop + 240;
        return {
          overflowY: style.overflowY,
          clientHeight: el.clientHeight,
          scrollHeight: el.scrollHeight,
          beforeTop,
          afterTop: el.scrollTop,
          canScroll
        };
      }"""
    )

    (ARTIFACTS_DIR / "panel-metrics.json").write_text(json.dumps(panel_state, indent=2))

    if not panel_state["canScroll"]:
        raise AssertionError("Edit-ops panel container is not scrollable.")
    if panel_state["afterTop"] <= panel_state["beforeTop"]:
        raise AssertionError("Edit-ops panel container did not scroll.")


def main() -> None:
    config = get_config()
    backend_url = config.base_url.rstrip("/")
    frontend_url = _frontend_url(backend_url)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        _stub_edit_ops(page)
        _login(page, base_url=frontend_url, email=config.email, password=config.password)
        _open_first_tool_editor(page, base_url=frontend_url)

        _request_edit_ops(page)

        panel_header = page.get_by_text(re.compile(r"AI-förslag", re.IGNORECASE))
        expect(panel_header).to_be_visible()
        page.screenshot(path=str(ARTIFACTS_DIR / "edit-ops-panel.png"), full_page=True)

        _assert_panel_scroll(page)

        context.close()


if __name__ == "__main__":
    main()
