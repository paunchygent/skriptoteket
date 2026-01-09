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
    dialog.get_by_label(re.compile(r"E-post", re.IGNORECASE)).fill(email)
    dialog.get_by_label(re.compile(r"L.senord", re.IGNORECASE)).fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"V.lkommen", re.IGNORECASE))
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
        raise RuntimeError("No tools available to verify editor chat drawer.")

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        mode_button = page.get_by_role("button", name=re.compile(r"K.llkod", re.IGNORECASE))
        expect(mode_button).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(
                path=str(artifacts_dir / "open-editor-after-click-failure.png"),
                full_page=True,
            )
        raise


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-editor-chat")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        menu_button = page.get_by_role("button", name="Spara/Öppna", exact=True)
        expect(menu_button).to_be_visible()
        menu_button.click()
        menu = page.get_by_role("menu")
        expect(menu).to_be_visible()
        expect(menu.get_by_text("Spara", exact=True)).to_be_visible()
        expect(menu.get_by_text("Öppna sparade", exact=True)).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "save-open-menu.png"), full_page=True)

        drawer = page.get_by_role("dialog", name="Kodassistenten", exact=True)
        expect(drawer).to_be_visible()
        toggle = drawer.get_by_role(
            "button", name=re.compile(r"(Minimera|Expandera) kodassistenten", re.IGNORECASE)
        )
        expect(toggle).to_be_visible()
        chat_body = drawer.locator(".chat-body")
        if chat_body.get_attribute("aria-hidden") == "true":
            toggle.click()
            expect(chat_body).not_to_have_attribute("aria-hidden", "true")
        expect(
            drawer.get_by_text(re.compile(r"Beskriv ditt m.l eller problem", re.IGNORECASE))
        ).to_be_visible()
        message_input = drawer.get_by_placeholder(re.compile(r"Beskriv ditt m.l", re.IGNORECASE))
        expect(message_input).to_be_visible()
        clear_button = drawer.get_by_role("button", name="Ny chatt", exact=True)
        expect(clear_button).to_be_visible()
        send_button = drawer.get_by_role("button", name="Skicka", exact=True)
        expect(send_button).to_be_visible()
        propose_button = drawer.get_by_role(
            "button", name=re.compile(r"F.resl. .*ndringar", re.IGNORECASE)
        )
        expect(propose_button).to_be_visible()

        page.screenshot(path=str(artifacts_dir / "chat-drawer.png"), full_page=True)

        placeholder = drawer.get_by_text(
            re.compile(r"Beskriv ditt m.l eller problem", re.IGNORECASE)
        )
        if clear_button.is_enabled():
            clear_button.click()
        expect(placeholder).to_be_visible()

        messages = drawer.locator("li")

        message_input.click()
        message_input.type("Hej!")
        expect(message_input).to_have_value(re.compile(r".+"))
        expect(send_button).to_be_enabled()
        send_button.click()

        expect(drawer.get_by_text("Hej!", exact=True)).to_be_visible()
        expect(placeholder).not_to_be_visible()

        warning = drawer.locator(".system-message-warning")

        deadline = time.time() + 10
        while time.time() < deadline:
            if warning.count() > 0 and warning.first.is_visible():
                break
            if messages.count() >= 2:
                break
            page.wait_for_timeout(250)
        else:
            raise AssertionError("No chat response or disabled message observed within timeout.")

        page.screenshot(path=str(artifacts_dir / "chat-drawer-after-send.png"), full_page=True)

        context.close()


if __name__ == "__main__":
    main()
