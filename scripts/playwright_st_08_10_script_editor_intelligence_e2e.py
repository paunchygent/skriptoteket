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


def _expect_autocomplete_option(page: object, label: str) -> None:
    tooltip = page.locator(".cm-tooltip-autocomplete").first
    expect(tooltip).to_be_visible(timeout=10_000)
    expect(tooltip).to_contain_text(label)


def _expect_hover_tooltip(page: object, *, signature: str, doc_snippet: str) -> None:
    tooltip = page.locator(".cm-tooltip-hover").first
    expect(tooltip).to_be_visible(timeout=10_000)
    expect(tooltip).to_contain_text(signature)
    expect(tooltip).to_contain_text(doc_snippet)


def _hover_codemirror_text(page: object, text: str) -> None:
    coords = page.evaluate(
        """
        (needle) => {
          const root = document.querySelector(".cm-editor .cm-content");
          if (!root) return null;

          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            const value = node.nodeValue ?? "";
            const idx = value.indexOf(needle);
            if (idx < 0) continue;

            const range = document.createRange();
            range.setStart(node, idx);
            range.setEnd(node, idx + needle.length);
            const rect = range.getBoundingClientRect();
            if (!rect || rect.width === 0 || rect.height === 0) continue;
            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
          }

          return null;
        }
        """,
        text,
    )
    if not coords or "x" not in coords or "y" not in coords:
        raise RuntimeError(f"Unable to find CodeMirror text node for hover: {text!r}")

    page.mouse.move(coords["x"], coords["y"])


def _expect_lint_message(page: object, message_snippet: str) -> None:
    marker = page.locator(".cm-lint-marker").first
    expect(marker).to_be_visible(timeout=10_000)
    marker.click()

    tooltip = page.locator(".cm-tooltip-lint").first
    expect(tooltip).to_be_visible(timeout=10_000)
    expect(tooltip).to_contain_text(message_snippet)
    page.keyboard.press("Escape")


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-08-10-script-editor-intelligence-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        _wait_for_intelligence_loaded(page)
        _clear_codemirror(page)
        page.keyboard.type("from ")
        _expect_autocomplete_option(page, "pdf_helper")
        _expect_autocomplete_option(page, "tool_errors")
        page.screenshot(path=str(artifacts_dir / "autocomplete-from.png"), full_page=True)

        page.keyboard.press("Escape")
        page.keyboard.type("pdf_helper import ")
        _expect_autocomplete_option(page, "save_as_pdf")
        page.screenshot(path=str(artifacts_dir / "autocomplete-pdf-helper.png"), full_page=True)

        page.keyboard.press("Escape")
        page.keyboard.type("save_as_pdf\nfrom tool_errors import ToolUserError\n")
        page.keyboard.press("Escape")

        cm_content = page.locator(".cm-editor .cm-content").first
        expect(cm_content).to_contain_text("save_as_pdf")
        expect(cm_content).to_contain_text("ToolUserError")

        _hover_codemirror_text(page, "save_as_pdf")
        _expect_hover_tooltip(
            page,
            signature="save_as_pdf(html, output_dir, filename) -> str",
            doc_snippet="Renderar HTML till PDF",
        )
        page.screenshot(path=str(artifacts_dir / "hover-save-as-pdf.png"), full_page=True)

        _hover_codemirror_text(page, "ToolUserError")
        _expect_hover_tooltip(
            page,
            signature="ToolUserError(message: str)",
            doc_snippet="Använd för fel som ska visas",
        )
        page.screenshot(path=str(artifacts_dir / "hover-tool-user-error.png"), full_page=True)

        _expect_lint_message(page, "Saknar startfunktion")
        page.screenshot(path=str(artifacts_dir / "lint-missing-entrypoint.png"), full_page=True)

        _clear_codemirror(page)
        page.keyboard.type("def run_tool(input_dir, out_dir):\n    return {}\n")
        _expect_lint_message(page, "Startfunktionen ska ta emot")
        page.screenshot(path=str(artifacts_dir / "lint-wrong-signature.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
