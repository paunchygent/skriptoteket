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
            "No tools available to verify ST-14-31.\n"
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


def _get_user_id(context: object, *, base_url: str) -> str:
    response = context.request.get(f"{base_url}/api/v1/auth/me")
    expect(response).to_be_ok()
    payload = response.json()
    user = payload.get("user") if isinstance(payload, dict) else None
    user_id = user.get("id") if isinstance(user, dict) else None
    if not user_id:
        raise RuntimeError("Expected user id in /api/v1/auth/me response.")
    return str(user_id)


def _assert_focus_mode_active(page: object) -> None:
    wrapper = page.locator(".auth-main-wrapper")
    expect(wrapper).to_have_class(re.compile(r".*is-focus-mode.*"))
    sidebar = page.locator(".sidebar").first
    expect(sidebar).to_be_hidden()


def _assert_focus_mode_inactive(page: object) -> None:
    wrapper = page.locator(".auth-main-wrapper")
    expect(wrapper).not_to_have_class(re.compile(r".*is-focus-mode.*"))


def _ensure_focus_mode_disabled(page: object) -> None:
    wrapper = page.locator(".auth-main-wrapper")
    is_active = wrapper.evaluate("el => el.classList.contains('is-focus-mode')")
    if not is_active:
        return

    exit_button = page.get_by_role("banner").get_by_role(
        "button", name=re.compile(r"Avsluta fokusläge", re.IGNORECASE)
    )
    if exit_button.count() == 0:
        raise RuntimeError("Expected focus mode exit control when focus mode is active.")
    exit_button.first.click()
    _assert_focus_mode_inactive(page)


def _storage_value(page: object, key: str) -> str | None:
    return page.evaluate("(storageKey) => localStorage.getItem(storageKey)", key)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-31-editor-focus-mode-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        _login(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
            artifacts_dir=artifacts_dir,
        )
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        user_id = _get_user_id(context, base_url=base_url)
        storage_key = f"skriptoteket:layout:focus_mode:{user_id}"

        _ensure_focus_mode_disabled(page)

        focus_toggle = page.get_by_role("main").get_by_role(
            "button", name=re.compile(r"Aktivera fokusläge", re.IGNORECASE)
        )
        expect(focus_toggle).to_be_visible(timeout=30_000)
        focus_toggle.first.click()

        expect(page.get_by_text("Fokusläge aktiverat")).to_be_visible(timeout=10_000)
        _assert_focus_mode_active(page)
        stored = _storage_value(page, storage_key)
        assert stored == "1", f"Expected {storage_key} to be '1' after enabling focus mode."
        page.screenshot(path=str(artifacts_dir / "focus-mode-enabled.png"), full_page=True)

        page.reload(wait_until="domcontentloaded")
        _assert_focus_mode_active(page)
        stored_after_reload = _storage_value(page, storage_key)
        assert stored_after_reload == "1", f"Expected {storage_key} to remain '1' after reload."

        expect(
            page.get_by_role("banner").get_by_role(
                "button", name=re.compile(r"Avsluta fokusläge", re.IGNORECASE)
            )
        ).to_be_visible(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "focus-mode-reload.png"), full_page=True)

        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        _assert_focus_mode_active(page)

        exit_button = page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"Avsluta fokusläge", re.IGNORECASE)
        )
        expect(exit_button).to_be_visible(timeout=30_000)
        exit_button.first.click()
        _assert_focus_mode_inactive(page)
        stored_after_exit = _storage_value(page, storage_key)
        assert stored_after_exit == "0", (
            f"Expected {storage_key} to be '0' after exiting focus mode."
        )
        page.screenshot(path=str(artifacts_dir / "focus-mode-disabled.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
