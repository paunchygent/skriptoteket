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


def _login_if_needed(page: object, *, email: str, password: str) -> None:
    login_modal = page.get_by_role("dialog")
    logout_button = page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))

    try:
        expect(logout_button).to_be_visible(timeout=2_000)
    except AssertionError:
        expect(login_modal).to_be_visible(timeout=30_000)
        login_modal.get_by_label("E-post").fill(email)
        login_modal.get_by_label("Lösenord").fill(password)
        login_modal.locator(
            "button[type='submit']",
            has_text=re.compile(r"Logga in", re.IGNORECASE),
        ).click()
        expect(logout_button).to_be_visible(timeout=30_000)


def _open_tool_run(page: object, *, base_url: str, slug: str) -> None:
    page.goto(f"{base_url}/tools/{slug}/run", wait_until="domcontentloaded")


def _ensure_tool_run_loaded(page: object, *, base_url: str, slug: str) -> None:
    """Ensure ToolRunView is mounted after login.

    Depending on router timing, the login modal redirect may not immediately mount the protected view.
    If the file input isn't present shortly after login, force a hard navigation to the tool route.
    """
    file_input = page.locator("input[type='file']")
    try:
        expect(file_input).to_have_count(1, timeout=5_000)
        return
    except AssertionError:
        _open_tool_run(page, base_url=base_url, slug=slug)
        expect(file_input).to_have_count(1, timeout=30_000)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-08-13-tool-usage-instructions")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    tool_slug = "demo-next-actions"
    toggle_label = re.compile(r"Så här gör du", re.IGNORECASE)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)

        # Context 1: should auto-open when unseen.
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        _open_tool_run(page, base_url=base_url, slug=tool_slug)
        _login_if_needed(page, email=email, password=password)
        _ensure_tool_run_loaded(page, base_url=base_url, slug=tool_slug)

        toggle = page.get_by_role("button", name=toggle_label)
        expect(toggle).to_have_attribute("aria-expanded", "true", timeout=30_000)
        page.screenshot(
            path=str(artifacts_dir / "usage-instructions-first-open.png"), full_page=True
        )

        toggle.click()
        expect(toggle).to_have_attribute("aria-expanded", "false", timeout=10_000)
        page.screenshot(
            path=str(artifacts_dir / "usage-instructions-collapsed.png"), full_page=True
        )

        context.close()

        # Context 2: should stay collapsed (state is persisted server-side).
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        _open_tool_run(page, base_url=base_url, slug=tool_slug)
        _login_if_needed(page, email=email, password=password)
        _ensure_tool_run_loaded(page, base_url=base_url, slug=tool_slug)

        toggle = page.get_by_role("button", name=toggle_label)
        expect(toggle).to_have_attribute("aria-expanded", "false", timeout=30_000)
        page.screenshot(
            path=str(artifacts_dir / "usage-instructions-second-device.png"), full_page=True
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
