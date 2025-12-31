from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_editor_smoke import _launch_chromium, _login, _open_editor


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
    content.focus()
    return content


def _set_codemirror_value(page: object, source_code: str) -> None:
    content = _focus_codemirror(page)
    content.fill(source_code)
    page.keyboard.press("Escape")


def _wait_for_intelligence_loaded(page: object) -> None:
    _set_codemirror_value(page, "x")
    marker = page.locator(".cm-lint-marker").first
    expect(marker).to_be_visible(timeout=15_000)
    page.keyboard.press("Escape")
    _set_codemirror_value(page, "")


def _wait_for_lint_markers(page: object, *, minimum: int) -> None:
    deadline = time.monotonic() + 15.0
    markers = page.locator(".cm-lint-marker")

    while time.monotonic() < deadline:
        if markers.count() >= minimum:
            return
        page.wait_for_timeout(250)

    raise AssertionError(f"Expected >= {minimum} lint markers, got {markers.count()}")


def _get_active_line_text(page: object) -> str:
    return str(
        page.evaluate(
            """
            () => {
              const line = document.querySelector(".cm-editor .cm-line.cm-activeLine");
              return (line?.textContent || "").trim();
            }
            """
        )
    )


def _expect_active_line_contains(page: object, expected: str) -> None:
    deadline = time.monotonic() + 3.0
    last = ""
    while time.monotonic() < deadline:
        last = _get_active_line_text(page)
        if expected in last:
            return
        page.wait_for_timeout(100)

    raise AssertionError(f"Expected active line to contain {expected!r}, got {last!r}")


def _press_open_lint_panel(page: object) -> None:
    page.keyboard.press("Meta+Shift+M")
    panel = page.locator(".cm-panel-lint").first
    if panel.is_visible():
        return
    page.keyboard.press("Control+Shift+M")


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-06-12-lint-panel-navigation-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        _wait_for_intelligence_loaded(page)

        _set_codemirror_value(
            page,
            "from pathlib import Path\n\n"
            "def run_tool(input_dir, output_dir):\n"
            '    raise ToolUserError("nope")\n'
            '    Path("x.txt").read_text()\n'
            '    return {"outputs": [], "next_actions": [], "state": {}}\n',
        )

        # Wait for linter recompute for this specific doc (marker counts can be stale between fills).
        _press_open_lint_panel(page)
        panel = page.locator(".cm-panel-lint").first
        expect(panel).to_be_visible(timeout=10_000)
        expect(panel).to_contain_text("ToolUserError används men import saknas")
        expect(panel).to_contain_text('encoding="utf-8"')

        # ST-06-13: gutter should only show error/warning markers (encoding is severity=info).
        markers = page.locator(".cm-lint-marker")
        expect(markers).to_have_count(1)

        # Keyboard navigation: next / previous diagnostic
        _focus_codemirror(page)
        page.keyboard.press("F8")
        _expect_active_line_contains(page, "ToolUserError")

        page.keyboard.press("F8")
        _expect_active_line_contains(page, "read_text")

        page.keyboard.press("Shift+F8")
        _expect_active_line_contains(page, "ToolUserError")

        # macOS fallback bindings
        page.keyboard.press("Meta+Alt+N")
        _expect_active_line_contains(page, "read_text")

        page.keyboard.press("Meta+Alt+P")
        _expect_active_line_contains(page, "ToolUserError")

        # Lint panel open + contents + quick-fix actions
        # Panel is already open from the wait step.
        expect(panel.get_by_role("button", name="Lägg till import")).to_be_visible()
        expect(panel.get_by_role("button", name="Lägg till encoding")).to_be_visible()

        page.screenshot(path=str(artifacts_dir / "lint-panel.png"), full_page=True)
        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
