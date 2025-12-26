from __future__ import annotations

import re
import time
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


def _read_entrypoint_name(page: object) -> str:
    select = page.locator("#tool-entrypoint").first
    expect(select).to_be_visible(timeout=30_000)

    value = (select.input_value() or "").strip()
    if value and value != "__custom__":
        return value

    custom_input = select.locator("xpath=following-sibling::input[1]")
    if custom_input.count() > 0:
        custom_value = (custom_input.input_value() or "").strip()
        if custom_value:
            return custom_value

    return "run_tool"


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
    return content


def _clear_codemirror(page: object) -> None:
    content = _focus_codemirror(page)
    content.fill("")
    content.click()


def _set_codemirror_value(page: object, source_code: str) -> None:
    content = _focus_codemirror(page)
    content.fill(source_code)


def _wait_for_intelligence_loaded(page: object) -> None:
    _clear_codemirror(page)
    page.keyboard.type("x")
    marker = page.locator(".cm-lint-marker").first
    expect(marker).to_be_visible(timeout=15_000)
    page.keyboard.press("Escape")
    _clear_codemirror(page)


def _expect_autocomplete_option(
    page: object, label: str, *, artifacts_dir: Path | None = None, checkpoint: str | None = None
) -> None:
    tooltip = page.locator(".cm-tooltip-autocomplete").first
    try:
        expect(tooltip).to_be_visible(timeout=5_000)
    except AssertionError as exc:
        if artifacts_dir and checkpoint:
            page.screenshot(
                path=str(artifacts_dir / f"{checkpoint}-autocomplete-missing.png"), full_page=True
            )

        # Debug helper: see whether completions exist at all if explicitly invoked.
        page.keyboard.press("Control+Space")
        try:
            expect(tooltip).to_be_visible(timeout=2_000)
        except AssertionError:
            raise exc

        if artifacts_dir and checkpoint:
            page.screenshot(
                path=str(artifacts_dir / f"{checkpoint}-autocomplete-after-ctrl-space.png"),
                full_page=True,
            )
        raise AssertionError(
            "Autocomplete did not open automatically while typing; it does open on Ctrl+Space."
        ) from exc

    expect(tooltip).to_contain_text(label)


def _expect_any_lint_message(page: object, message_snippet: str) -> None:
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
                page.keyboard.press("Escape")
                return

            page.keyboard.press("Escape")

        page.wait_for_timeout(250)

    details = "\n---\n".join(seen_tooltips) if seen_tooltips else "<no lint tooltips captured>"
    raise AssertionError(
        f"Expected lint message snippet not found: {message_snippet!r}\n"
        f"Seen lint tooltips:\n{details}"
    )


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-08-11-script-editor-intelligence-phase2-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        entrypoint = _read_entrypoint_name(page)
        _wait_for_intelligence_loaded(page)

        # 1) Contract key completions inside return dict
        _clear_codemirror(page)
        page.keyboard.type(f'def {entrypoint}(input_dir, output_dir):\n    return {{\n        "')
        page.keyboard.type("o")
        _expect_autocomplete_option(
            page, "outputs", artifacts_dir=artifacts_dir, checkpoint="contract-outputs"
        )
        page.keyboard.press("Escape")
        page.keyboard.press("Backspace")
        page.keyboard.type("n")
        _expect_autocomplete_option(
            page, "next_actions", artifacts_dir=artifacts_dir, checkpoint="contract-next"
        )
        page.keyboard.press("Escape")
        page.keyboard.press("Backspace")
        page.keyboard.type("s")
        _expect_autocomplete_option(
            page, "state", artifacts_dir=artifacts_dir, checkpoint="contract-state"
        )
        page.screenshot(path=str(artifacts_dir / "contract-key-completions.png"), full_page=True)

        # 2) Lint: missing outputs -> info diagnostic
        _set_codemirror_value(
            page,
            f"def {entrypoint}(input_dir, output_dir):\n"
            "    return {\n"
            '        "next_actions": [],\n'
            '        "state": None,\n'
            "    }\n",
        )
        _expect_any_lint_message(page, "Retur-dict saknar nycklar: outputs")
        page.screenshot(path=str(artifacts_dir / "lint-missing-outputs.png"), full_page=True)

        # 3) Lint: invalid kind warns and lists allowed kinds
        _set_codemirror_value(
            page,
            f"def {entrypoint}(input_dir, output_dir):\n"
            "    return {\n"
            '        "outputs": [{"kind": "nope"}],\n'
            '        "next_actions": [],\n'
            '        "state": None,\n'
            "    }\n",
        )
        _expect_any_lint_message(page, 'Ogiltigt kind: "nope".')
        _expect_any_lint_message(page, "Tillåtna: notice, markdown, table, json, html_sandboxed.")
        page.screenshot(path=str(artifacts_dir / "lint-invalid-kind.png"), full_page=True)

        # 4) Security: blocked network + shell exec
        _set_codemirror_value(
            page,
            "import requests\n"
            "import subprocess\n"
            "\n"
            f"def {entrypoint}(input_dir, output_dir):\n"
            '    subprocess.run(["echo", "hej"])\n'
            '    return {"outputs": [], "next_actions": [], "state": None}\n',
        )
        _expect_any_lint_message(page, "Nätverksbibliotek stöds inte i sandbox")
        _expect_any_lint_message(page, "Undvik subprocess/os.system i sandbox")
        page.screenshot(path=str(artifacts_dir / "lint-security.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
