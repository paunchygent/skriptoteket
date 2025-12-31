from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Route, expect, sync_playwright

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
        message = str(exc)
        if "MachPortRendezvousServer" in message or "Permission denied (1100)" in message:
            print("Headless Chromium failed with macOS permission error; retrying headful.")
            return playwright.chromium.launch(headless=False)

        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")

    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    expect(page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))).to_be_visible(
        timeout=15_000
    )


def _open_editor(page: object, *, base_url: str, artifacts_dir: Path | None = None) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / "open-editor-failure.png"), full_page=True)
        raise

    empty_state = page.get_by_text("Inga verktyg finns.")
    if empty_state.count() > 0 and empty_state.is_visible():
        raise RuntimeError(
            "No tools available to verify editor intelligence.\n"
            "Seed a tool via the script bank, then retry (see docs/runbooks/runbook-script-bank-seeding.md)."
        )

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        expect(
            page.get_by_role(
                "heading",
                name=re.compile(r"(Testkör kod|Testkor kod|Källkod|Kallkod)", re.IGNORECASE),
            ).first
        ).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(
                path=str(artifacts_dir / "open-editor-after-click-failure.png"),
                full_page=True,
            )
        raise


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
    return content


def _clear_codemirror(page: object) -> None:
    content = _focus_codemirror(page)
    content.fill("")
    content.click()


def _wait_for_intelligence_loaded(page: object) -> None:
    _clear_codemirror(page)
    page.keyboard.type("x")
    marker = page.locator(".cm-lint-marker").first
    expect(marker).to_be_visible(timeout=15_000)
    page.keyboard.press("Escape")
    _clear_codemirror(page)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-08-14-ai-inline-completions-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    completion_payload = (
        "return {\n"
        '        "outputs": [{"kind": "notice", "level": "info", "message": "Klart!"}],\n'
        '        "next_actions": [],\n'
        '        "state": None,\n'
        "    }\n"
    )

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def handle_completions(route: Route) -> None:
            request = route.request
            csrf = request.headers.get("x-csrf-token")
            if not csrf:
                raise AssertionError("Expected X-CSRF-Token header on /completions request")

            body = request.post_data or ""
            payload = json.loads(body) if body else {}
            assert "prefix" in payload and "suffix" in payload

            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"completion": completion_payload, "enabled": True}),
            )

        page.route("**/api/v1/editor/completions", handle_completions)

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _wait_for_intelligence_loaded(page)

        _clear_codemirror(page)
        page.keyboard.type("def run_tool(input_dir, output_dir):\n    ")

        ghost = page.locator(".cm-skriptoteket-ghost-text").first
        expect(ghost).to_be_visible(timeout=10_000)
        expect(ghost).to_contain_text("return {")
        page.screenshot(path=str(artifacts_dir / "ghost-text-visible.png"), full_page=True)

        page.keyboard.press("Tab")
        content = page.locator(".cm-editor .cm-content").first
        expect(content).to_contain_text("return {")
        expect(page.locator(".cm-skriptoteket-ghost-text")).to_have_count(0)
        page.screenshot(path=str(artifacts_dir / "ghost-text-accepted.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
