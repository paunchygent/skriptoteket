from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config
from scripts.playwright_ui_editor_smoke import _launch_chromium, _login, _open_editor


def _dom_click_tooltip_action(page: object, action_label: str) -> bool:
    return bool(
        page.evaluate(
            """
            (label) => {
              const tooltip = document.querySelector(".cm-tooltip-lint");
              if (!tooltip) return false;
              const want = label.trim().toLowerCase();

              const actions = Array.from(tooltip.querySelectorAll("button, a"));
              const match = actions.find((node) => {
                const text = (node.textContent || "").trim().toLowerCase();
                const aria = (node.getAttribute("aria-label") || "").trim().toLowerCase();
                return text === want || text.includes(want) || aria.includes(want);
              });

              if (!match) return false;
              match.click();
              return true;
            }
            """,
            action_label,
        )
    )


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
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


def _press_open_lint_panel(page: object) -> object:
    page.keyboard.press("Meta+Shift+M")
    panel = page.locator(".cm-panel-lint").first
    if panel.is_visible():
        return panel
    page.keyboard.press("Control+Shift+M")
    return panel


def _apply_quick_fix_in_lint_panel(
    page: object,
    *,
    message_snippet: str,
    action_label: str,
    artifacts_dir: Path | None = None,
    checkpoint: str | None = None,
) -> None:
    panel = _press_open_lint_panel(page)
    expect(panel).to_be_visible(timeout=10_000)
    expect(panel).to_contain_text(message_snippet, timeout=10_000)

    button = panel.get_by_role("button", name=action_label).first
    expect(button).to_be_visible(timeout=10_000)

    if artifacts_dir and checkpoint:
        (artifacts_dir / f"{checkpoint}-panel.html").write_text(
            panel.inner_html() or "", encoding="utf-8"
        )
        page.screenshot(
            path=str(artifacts_dir / f"{checkpoint}-panel-before-click.png"), full_page=True
        )

    button.click()
    page.wait_for_timeout(100)
    if button.is_visible():
        button.click()

    if artifacts_dir and checkpoint:
        page.screenshot(
            path=str(artifacts_dir / f"{checkpoint}-panel-after-click.png"), full_page=True
        )

    page.keyboard.press("Escape")


def _apply_quick_fix(
    page: object,
    *,
    message_snippet: str,
    action_label: str,
    artifacts_dir: Path | None = None,
    checkpoint: str | None = None,
) -> None:
    deadline = time.monotonic() + 15.0
    seen_tooltips: list[str] = []

    while time.monotonic() < deadline:
        markers = page.locator(".cm-lint-marker")
        if markers.count() == 0:
            page.wait_for_timeout(250)
            continue

        count = markers.count()
        seen_tooltips = []
        for index in range(count):
            marker = markers.nth(index)
            marker.click()

            tooltip = page.locator(".cm-tooltip-lint").first
            expect(tooltip).to_be_visible(timeout=10_000)
            text = (tooltip.inner_text() or "").strip()
            if text:
                seen_tooltips.append(text)

            if message_snippet in text:
                if artifacts_dir and checkpoint:
                    (artifacts_dir / f"{checkpoint}-tooltip.html").write_text(
                        tooltip.inner_html() or "", encoding="utf-8"
                    )
                    page.screenshot(
                        path=str(artifacts_dir / f"{checkpoint}-before-click.png"),
                        full_page=True,
                    )

                # Verify idempotency by clicking twice before lint recomputes.
                clicked = _dom_click_tooltip_action(page, action_label)
                if not clicked:
                    if artifacts_dir and checkpoint:
                        page.screenshot(
                            path=str(artifacts_dir / f"{checkpoint}-missing-action.png"),
                            full_page=True,
                        )
                    raise AssertionError(
                        f"Expected quick fix action not found: {action_label!r}\n\nTooltip text:\n{text}"
                    )

                page.wait_for_timeout(100)
                _dom_click_tooltip_action(page, action_label)

                if artifacts_dir and checkpoint:
                    page.screenshot(
                        path=str(artifacts_dir / f"{checkpoint}-after-click.png"),
                        full_page=True,
                    )

                page.keyboard.press("Escape")
                return

            page.keyboard.press("Escape")

        page.wait_for_timeout(250)

    details = "\n---\n".join(seen_tooltips) if seen_tooltips else "<no lint tooltips captured>"
    raise AssertionError(
        f"Expected lint message snippet not found: {message_snippet!r}\n"
        f"Seen lint tooltips:\n{details}"
    )


def _expect_editor_contains(page: object, text: str) -> None:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_contain_text(text)


def _expect_editor_count(page: object, needle: str, expected: int) -> None:
    content = page.locator(".cm-editor .cm-content").first
    value = (content.inner_text() or "").strip()
    found = value.count(needle)
    assert found == expected, (
        f"Expected {expected} occurrences of {needle!r}, found {found}\n\nEditor text:\n{value}"
    )


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-06-11-quick-fix-actions-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        _wait_for_intelligence_loaded(page)

        # 1) ToolUserError missing import
        _set_codemirror_value(
            page,
            'def run_tool(input_dir, output_dir):\n    raise ToolUserError("nope")\n',
        )
        page.wait_for_timeout(1_000)
        _apply_quick_fix(
            page,
            message_snippet="ToolUserError används men import saknas",
            action_label="Lägg till import",
            artifacts_dir=artifacts_dir,
            checkpoint="toolusererror-import",
        )
        _expect_editor_contains(page, "from tool_errors import ToolUserError")
        _expect_editor_count(page, "from tool_errors import ToolUserError", 1)

        # 2) Encoding missing
        _set_codemirror_value(
            page,
            "from pathlib import Path\n\n"
            "def run_tool(input_dir, output_dir):\n"
            '    Path("x.txt").read_text()\n'
            '    return {"outputs": [], "next_actions": [], "state": {}}\n',
        )
        page.wait_for_timeout(1_000)
        _apply_quick_fix_in_lint_panel(
            page,
            message_snippet='encoding="utf-8"',
            action_label="Lägg till encoding",
            artifacts_dir=artifacts_dir,
            checkpoint="encoding",
        )
        _expect_editor_contains(page, 'read_text(encoding="utf-8")')
        _expect_editor_count(page, 'encoding="utf-8"', 1)

        # 3) Entrypoint missing
        _set_codemirror_value(page, "def helper():\n    return 1\n")
        page.wait_for_timeout(1_000)
        _apply_quick_fix(
            page,
            message_snippet="Saknar startfunktion",
            action_label="Skapa startfunktion",
            artifacts_dir=artifacts_dir,
            checkpoint="entrypoint",
        )
        _expect_editor_contains(page, "def run_tool(input_dir, output_dir):")
        _expect_editor_count(page, "def run_tool(input_dir, output_dir):", 1)

        # 4) Contract keys missing
        _set_codemirror_value(
            page, 'def run_tool(input_dir, output_dir):\n    return {"outputs": []}\n'
        )
        page.wait_for_timeout(1_000)
        _apply_quick_fix_in_lint_panel(
            page,
            message_snippet="Retur-dict saknar nycklar",
            action_label="Lägg till nycklar",
            artifacts_dir=artifacts_dir,
            checkpoint="contract-keys",
        )
        _expect_editor_contains(page, '"next_actions": []')
        _expect_editor_contains(page, '"state": {}')
        _expect_editor_count(page, '"next_actions"', 1)
        _expect_editor_count(page, '"state"', 1)

        page.screenshot(path=str(artifacts_dir / "done.png"), full_page=True)
        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
