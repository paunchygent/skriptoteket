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
            executable_path = _find_chromium_headless_shell()
            if executable_path:
                print(
                    "Headless Chromium failed with macOS permission error; retrying with headless shell."
                )
                return playwright.chromium.launch(headless=True, executable_path=executable_path)
            raise

        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(page: object, *, base_url: str, email: str, password: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible(timeout=30_000)
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    try:
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
    except AssertionError:
        page.screenshot(path=str(artifacts_dir / "login-failure.png"), full_page=True)
        raise


def _open_editor(page: object, *, base_url: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")

    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
    except AssertionError:
        page.screenshot(path=str(artifacts_dir / "open-editor-failure.png"), full_page=True)
        raise

    empty_state = page.get_by_text("Inga verktyg finns.")
    if empty_state.count() > 0 and empty_state.is_visible():
        raise RuntimeError(
            "No tools available to verify ST-14-30.\n"
            "Seed a tool via the script bank, then retry (see docs/runbooks/runbook-script-bank-seeding.md)."
        )

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible(timeout=30_000)
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")

    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"Källkod", re.IGNORECASE)).first
        ).to_be_visible(timeout=30_000)
    except AssertionError:
        page.screenshot(
            path=str(artifacts_dir / "open-editor-after-click-failure.png"), full_page=True
        )
        raise


def _ensure_can_edit(page: object) -> None:
    takeover_button = page.get_by_role("button", name=re.compile(r"Ta över lås", re.IGNORECASE))
    if takeover_button.count() > 0 and takeover_button.first.is_visible():
        takeover_button.first.click()
        expect(
            page.get_by_text(re.compile(r"Du har redigeringslåset", re.IGNORECASE))
        ).to_be_visible(timeout=20_000)


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
    return content


def _set_source_code(page: object, code: str) -> None:
    content = _focus_codemirror(page)
    content.fill("")
    content.click()
    page.keyboard.type(code)


def _assert_restore_prompt_visible(page: object) -> None:
    expect(page.get_by_text("Lokalt arbetsexemplar hittades")).to_be_visible(timeout=15_000)


def _assert_restore_prompt_hidden(page: object) -> None:
    expect(page.get_by_text("Lokalt arbetsexemplar hittades")).to_have_count(0)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-30-editor-working-copy-persistence-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.on("dialog", lambda dialog: dialog.accept())

        _login(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
            artifacts_dir=artifacts_dir,
        )
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _ensure_can_edit(page)

        # Flow A: create working copy → reload → discard → reload verifies cleared.
        expect(page.get_by_text("Lokalt arbetsexemplar hittades")).to_have_count(0)

        _set_source_code(
            page,
            "def run_tool(input_dir, output_dir):\n    # WORKING_COPY_E2E_A\n    return None\n",
        )
        page.wait_for_timeout(1800)  # Debounced head save (1200ms) + slack.
        page.reload(wait_until="domcontentloaded")

        _assert_restore_prompt_visible(page)
        page.screenshot(path=str(artifacts_dir / "restore-prompt-visible-a.png"), full_page=True)

        page.get_by_role("button", name=re.compile(r"Visa diff", re.IGNORECASE)).click()
        expect(
            page.get_by_text(
                re.compile(r"Serverversion\s*→\s*Lokalt arbetsexemplar", re.IGNORECASE)
            )
        ).to_be_visible(timeout=15_000)
        page.screenshot(path=str(artifacts_dir / "restore-diff-modal-a.png"), full_page=True)
        page.locator("button", has_text="×").first.click()

        page.get_by_role("button", name=re.compile(r"Kasta lokalt", re.IGNORECASE)).click()
        expect(page.get_by_text("Lokalt arbetsexemplar hittades")).to_have_count(0)
        page.reload(wait_until="domcontentloaded")
        _assert_restore_prompt_hidden(page)
        page.screenshot(path=str(artifacts_dir / "restore-prompt-cleared-a.png"), full_page=True)

        # Flow B: create working copy → reload → restore → pinned checkpoint → clear local.
        _set_source_code(
            page,
            "def run_tool(input_dir, output_dir):\n    # WORKING_COPY_E2E_B\n    return None\n",
        )
        page.wait_for_timeout(1800)
        page.reload(wait_until="domcontentloaded")
        _assert_restore_prompt_visible(page)
        page.screenshot(path=str(artifacts_dir / "restore-prompt-visible-b.png"), full_page=True)

        page.get_by_role("button", name=re.compile(r"Återställ lokalt", re.IGNORECASE)).click()
        _assert_restore_prompt_hidden(page)
        expect(page.locator(".cm-editor .cm-content").first).to_contain_text("WORKING_COPY_E2E_B")
        page.screenshot(path=str(artifacts_dir / "working-copy-restored.png"), full_page=True)

        page.get_by_role("button", name="Öppna sparade").click()
        drawer = page.get_by_role("dialog", name="Öppna sparade")
        expect(drawer).to_be_visible(timeout=15_000)

        drawer.get_by_placeholder("Etikett (valfri)").fill("E2E pinned checkpoint")
        drawer.get_by_role(
            "button", name=re.compile(r"Skapa återställningspunkt", re.IGNORECASE)
        ).click()
        expect(drawer.get_by_text("E2E pinned checkpoint")).to_be_visible(timeout=15_000)
        page.screenshot(path=str(artifacts_dir / "pinned-checkpoint-created.png"), full_page=True)

        drawer.get_by_role(
            "button", name=re.compile(r"Återställ till serverversion", re.IGNORECASE)
        ).click()
        expect(drawer.get_by_text("Inga lokala återställningspunkter ännu.")).to_be_visible(
            timeout=15_000
        )
        expect(page.locator(".cm-editor .cm-content").first).not_to_contain_text(
            "WORKING_COPY_E2E_B"
        )
        page.screenshot(path=str(artifacts_dir / "restore-server-clears-local.png"), full_page=True)

        page.reload(wait_until="domcontentloaded")
        _assert_restore_prompt_hidden(page)
        page.screenshot(path=str(artifacts_dir / "restore-prompt-cleared-b.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
