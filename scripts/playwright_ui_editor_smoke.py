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
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        message = str(exc)
        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(
    page: object, *, base_url: str, email: str, password: str, artifacts_dir: Path | None = None
) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")

    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / "login-failure.png"), full_page=True)
        raise


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
        raise RuntimeError("No tools available to verify editor view.")

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        editor = page.locator(".cm-editor").first
        expect(editor).to_be_visible(timeout=30_000)
    except AssertionError:
        if artifacts_dir:
            page.screenshot(
                path=str(artifacts_dir / "open-editor-after-click-failure.png"),
                full_page=True,
            )
        raise

    chat_title = page.get_by_role("heading", name=re.compile(r"Kodassistenten", re.IGNORECASE))
    try:
        expect(chat_title).to_be_visible(timeout=30_000)
    except AssertionError:
        if artifacts_dir:
            page.screenshot(
                path=str(artifacts_dir / "chat-drawer-missing.png"),
                full_page=True,
            )
        raise


def _assert_panel_fill(
    page: object,
    *,
    panel_state_selector: str,
    panel_selector: str,
    min_ratio: float,
    artifacts_dir: Path | None,
    screenshot_name: str,
    label: str,
) -> bool:
    panel_state = page.locator(panel_state_selector)
    if panel_state.count() == 0:
        return False

    panel_state = panel_state.first
    if not panel_state.is_visible():
        return False

    panel = page.locator(panel_selector).first
    expect(panel).to_be_visible()

    empty_box = panel_state.bounding_box()
    panel_box = panel.bounding_box()
    if not empty_box or not panel_box or panel_box["height"] == 0:
        raise RuntimeError(f"{label} layout could not be measured.")

    ratio = empty_box["height"] / panel_box["height"]
    if ratio < min_ratio:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / screenshot_name), full_page=True)
        raise RuntimeError(
            f"{label} empty state height ratio too small: {ratio:.2f} < {min_ratio:.2f}."
        )

    return True


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-editor-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        editor = page.locator(".cm-editor").first
        expect(editor).to_be_visible(timeout=30_000)

        chat_input = page.locator("textarea[placeholder^='Beskriv']").first
        try:
            expect(chat_input).to_be_editable()
            chat_input.fill("Ping")
            expect(chat_input).to_have_value("Ping")
            chat_input.fill("")
            expect(page.locator(".chat-body--collapsed")).to_have_count(0)
        except AssertionError:
            page.screenshot(path=str(artifacts_dir / "chat-input-not-editable.png"), full_page=True)
            raise

        diff_mode_button = page.get_by_role("button", name=re.compile(r"^Diff$", re.IGNORECASE))
        if diff_mode_button.count() > 0:
            diff_mode_button.first.click()
            page.screenshot(path=str(artifacts_dir / "diff-mode.png"), full_page=True)
            close_diff_button = page.get_by_role(
                "button", name=re.compile(r"Stäng diff", re.IGNORECASE)
            )
            if close_diff_button.count() > 0:
                close_diff_button.first.click()
                page.screenshot(path=str(artifacts_dir / "diff-empty-state.png"), full_page=True)
            _assert_panel_fill(
                page,
                panel_state_selector=".cm-mergeView",
                panel_selector="[data-editor-panel='mode']",
                min_ratio=0.75,
                artifacts_dir=artifacts_dir,
                screenshot_name="diff-merge-height.png",
                label="Diff",
            )

        test_mode_button = page.get_by_role("button", name="Testkör").first
        expect(test_mode_button).to_be_visible()
        test_mode_button.click()
        page.screenshot(path=str(artifacts_dir / "test-mode.png"), full_page=True)

        _assert_panel_fill(
            page,
            panel_state_selector="[data-editor-panel='test']",
            panel_selector="[data-editor-panel='mode']",
            min_ratio=0.55,
            artifacts_dir=artifacts_dir,
            screenshot_name="test-panel-height.png",
            label="Testkör",
        )

        entrypoint_select = page.get_by_label("Startfunktion", exact=True)
        expect(entrypoint_select).to_be_visible()
        expect(
            entrypoint_select.locator("option", has_text=re.compile(r"^run_tool$", re.IGNORECASE))
        ).to_have_count(1)
        expect(
            entrypoint_select.locator("option", has_text=re.compile(r"^Eget", re.IGNORECASE))
        ).to_have_count(1)
        expect(
            entrypoint_select.locator("option", has_text=re.compile(r"^main$", re.IGNORECASE))
        ).to_have_count(0)
        expect(
            entrypoint_select.locator("option", has_text=re.compile(r"^run$", re.IGNORECASE))
        ).to_have_count(0)
        expect(
            entrypoint_select.locator("option", has_text=re.compile(r"^execute$", re.IGNORECASE))
        ).to_have_count(0)

        help_text = page.get_by_text(
            re.compile(r"funktion i skriptet som tar", re.IGNORECASE)
        ).first
        expect(help_text).to_be_visible()

        sandbox_section_label = page.get_by_role("button", name="Testkör kod")
        if sandbox_section_label.count() == 0:
            save_menu_button = page.get_by_role("button", name="Spara/Öppna").first
            expect(save_menu_button).to_be_visible()
            save_menu_button.click()

            save_button = page.get_by_role(
                "menuitem",
                name=re.compile(r"^(Spara|Skapa ny) arbetsversion$", re.IGNORECASE),
            )
            if save_button.count() == 0:
                if artifacts_dir:
                    page.screenshot(
                        path=str(artifacts_dir / "missing-save-work-version.png"),
                        full_page=True,
                    )
                raise RuntimeError(
                    "Sandbox runner missing and no 'Spara arbetsversion'/'Skapa ny arbetsversion' menu item found."
                )
            save_button.first.click()
            page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")

            test_mode_button = page.get_by_role("button", name="Testkör").first
            expect(test_mode_button).to_be_visible()
            test_mode_button.click()

        inputs_summary_locator = page.locator(
            "summary", has_text=re.compile(r"Indata\s*\(JSON\)", re.IGNORECASE)
        )
        try:
            expect(inputs_summary_locator).to_have_count(1, timeout=30_000)
        except AssertionError:
            page.screenshot(path=str(artifacts_dir / "missing-inputs-summary.png"), full_page=True)
            global_summary_count = page.locator("summary").count()
            global_indata_count = page.locator(
                "summary", has_text=re.compile(r"Indata\s*\(JSON\)", re.IGNORECASE)
            ).count()
            raise RuntimeError(
                "Could not find the 'Indata (JSON)' <summary> in the sandbox runner.\n"
                f"Global <summary> count: {global_summary_count}\n"
                f"Global 'Indata (JSON)' summary count: {global_indata_count}\n"
                "Screenshot written to missing-inputs-summary.png"
            )

        inputs_summary = inputs_summary_locator.first
        expect(inputs_summary).to_be_visible(timeout=30_000)
        sandbox = inputs_summary.locator("xpath=ancestor::div[contains(@class,'space-y-4')][1]")

        choose_files_label = sandbox.get_by_text(re.compile(r"Välj filer", re.IGNORECASE))
        if choose_files_label.count() > 0:
            file_input = sandbox.locator("input[type='file']")
            expect(file_input).to_have_count(1, timeout=30_000)

        inputs_summary.click()
        expect(sandbox.get_by_text("SKRIPTOTEKET_INPUTS")).to_be_visible(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "editor-loaded.png"), full_page=True)

        action_button = page.get_by_role(
            "button",
            name=re.compile(r"(Begär publicering|Publicera|Avslå)", re.IGNORECASE),
        )
        if action_button.count() > 0:
            action_button.first.click()
            dialog = page.locator("[aria-labelledby='workflow-modal-title']").first
            if dialog.count() > 0:
                expect(dialog).to_be_visible()
                cancel_button = dialog.get_by_role("button", name="Avbryt")
                close_button = dialog.get_by_role("button", name="Stäng")
                if cancel_button.count() > 0:
                    cancel_button.first.click()
                elif close_button.count() > 0:
                    close_button.first.click()
                expect(dialog).not_to_be_visible()

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
