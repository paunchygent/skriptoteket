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


def _open_first_tool_editor(
    page: object, *, base_url: str, artifacts_dir: Path | None = None
) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"(Verktyg|Testyta)", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / "open-tools-failure.png"), full_page=True)
        raise

    empty_state = page.get_by_text("Inga verktyg finns.")
    if empty_state.count() > 0 and empty_state.is_visible():
        raise RuntimeError("No tools available to verify working copy diff modal.")

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        mode_button = page.get_by_role("button", name=re.compile(r"K.llkod", re.IGNORECASE))
        expect(mode_button).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / "open-editor-failure.png"), full_page=True)
        raise


def _inject_large_working_copy_change(page: object, *, lines: int) -> None:
    editor = page.locator(".cm-content").first
    expect(editor).to_be_visible()
    editor.click()

    payload = "\n" + "\n".join([f"# filler {idx}" for idx in range(lines)]) + "\n"
    page.keyboard.insert_text(payload)

    # Working copy head persistence is debounced; give it time.
    page.wait_for_timeout(1700)


def _wait_for_working_copy_prompt(page: object, *, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    locator = page.get_by_text(re.compile(r"Lokalt arbetsexemplar hittades", re.IGNORECASE))
    while time.time() < deadline:
        if locator.count() > 0 and locator.first.is_visible():
            return
        page.wait_for_timeout(200)
    raise AssertionError("Working copy restore prompt did not appear after reload.")


def _open_diff_modal(page: object) -> object:
    page.get_by_role("button", name=re.compile(r"Visa diff", re.IGNORECASE)).click()

    modal = page.locator('[role="dialog"]').filter(has=page.locator("#editor-diff-file")).first
    expect(modal).to_be_visible()
    return modal


def _assert_diff_modal_scrollable(modal: object) -> None:
    # MergeView uses `.cm-mergeView` as the scroll container (editors expand to content height).
    merge_containers = modal.locator(".cm-mergeView")
    if merge_containers.count() > 0:
        container = merge_containers.first
        expect(container).to_be_visible()
        scroll_state = container.evaluate(
            """(el) => {
            const beforeTop = el.scrollTop;
            const canScroll = el.scrollHeight > el.clientHeight;
            el.scrollTop = beforeTop + 240;
            return { beforeTop, afterTop: el.scrollTop, canScroll };
          }"""
        )

        if not scroll_state["canScroll"]:
            raise AssertionError(
                "Merge diff container is not scrollable (scrollHeight <= clientHeight)."
            )
        if scroll_state["afterTop"] <= scroll_state["beforeTop"]:
            raise AssertionError("Merge diff container did not scroll when updating scrollTop.")
        return

    scrollers = modal.locator(".cm-scroller")
    count = scrollers.count()
    if count == 0:
        raise AssertionError("Diff modal did not contain any CodeMirror scroll containers.")

    for idx in range(count):
        scroller = scrollers.nth(idx)
        expect(scroller).to_be_visible()
        scroll_state = scroller.evaluate(
            """(el) => {
            const beforeTop = el.scrollTop;
            const canScroll = el.scrollHeight > el.clientHeight;
            el.scrollTop = beforeTop + 240;
            return { beforeTop, afterTop: el.scrollTop, canScroll };
          }"""
        )
        if scroll_state["canScroll"] and scroll_state["afterTop"] > scroll_state["beforeTop"]:
            return

    raise AssertionError("No diff container was scrollable (scrollHeight <= clientHeight).")


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-working-copy-diff")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.on("dialog", lambda dialog: dialog.accept())

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)
        _open_first_tool_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)

        _inject_large_working_copy_change(page, lines=260)

        page.reload(wait_until="domcontentloaded")
        _wait_for_working_copy_prompt(page)
        page.screenshot(path=str(artifacts_dir / "restore-prompt.png"), full_page=True)

        modal = _open_diff_modal(page)
        expect(modal.locator('button:has-text("×")')).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "diff-modal.png"), full_page=True)

        try:
            _assert_diff_modal_scrollable(modal)
        except AssertionError:
            page.screenshot(
                path=str(artifacts_dir / "diff-modal-scroll-failure.png"), full_page=True
            )
            raise

        modal.locator('button:has-text("×")').click()
        expect(modal).not_to_be_visible()

        context.close()


if __name__ == "__main__":
    main()
