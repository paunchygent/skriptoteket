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
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("main").get_by_role(
        "button", name=re.compile(r"Logga in", re.IGNORECASE)
    ).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


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
        raise RuntimeError("No tools available to verify editor workflow actions.")

    edit_link = page.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")
    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"Testa i sandbox", re.IGNORECASE))
        ).to_be_visible()
    except AssertionError:
        if artifacts_dir:
            page.screenshot(
                path=str(artifacts_dir / "open-editor-after-click-failure.png"),
                full_page=True,
            )
        raise


def _open_actions_menu(page: object) -> None:
    actions_button = page.get_by_role("button", name=re.compile(r"Åtgärder", re.IGNORECASE))
    expect(actions_button).to_be_visible()
    actions_button.click()
    expect(page.get_by_role("menu")).to_be_visible()


def _action_available(page: object, label: str) -> bool:
    actions_button = page.get_by_role("button", name=re.compile(r"Åtgärder", re.IGNORECASE))
    if actions_button.is_disabled():
        return False

    actions_button.click()
    menu_item = page.get_by_role("menuitem", name=re.compile(label, re.IGNORECASE))
    is_visible = menu_item.count() > 0 and menu_item.is_visible()
    page.keyboard.press("Escape")
    return is_visible


def _select_action(page: object, label: str) -> None:
    _open_actions_menu(page)
    menu_item = page.get_by_role("menuitem", name=re.compile(label, re.IGNORECASE))
    expect(menu_item).to_be_visible()
    menu_item.click()


def _ensure_draft(page: object) -> None:
    if _action_available(page, "Begär publicering"):
        return

    create_button = page.get_by_role(
        "button",
        name=re.compile(r"^(Spara|Skapa ny) arbetsversion$", re.IGNORECASE),
    )
    if create_button.count() == 0 or not create_button.is_visible():
        raise RuntimeError(
            "Unable to create draft: no 'Spara arbetsversion'/'Skapa ny arbetsversion' button found."
        )

    create_button.click()
    page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")
    if not _action_available(page, "Begär publicering"):
        raise RuntimeError("Draft created but workflow action 'Begär publicering' not available.")


def _submit_for_review(page: object, note: str | None) -> str:
    _select_action(page, "Begär publicering")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    if note:
        dialog.get_by_placeholder("Skriv en kort notis…").fill(note)
    dialog.get_by_role("button", name=re.compile(r"Begär publicering", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()
    if not _action_available(page, "Publicera version"):
        raise RuntimeError("Expected publish action after requesting review.")
    return page.url.split("/admin/tool-versions/")[-1].split("?")[0]


def _request_changes(page: object, message: str | None) -> None:
    _select_action(page, "Begär ändringar")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    if message:
        dialog.get_by_placeholder("Beskriv vad som behöver ändras…").fill(message)
    dialog.get_by_role("button", name=re.compile(r"Begär ändringar", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()
    if not _action_available(page, "Begär publicering"):
        raise RuntimeError("Expected 'Begär publicering' after requesting changes.")


def _publish(page: object, summary: str | None) -> None:
    _select_action(page, "Publicera version")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    if summary:
        dialog.get_by_placeholder("T.ex. uppdaterade regler…").fill(summary)
    dialog.get_by_role("button", name=re.compile(r"Publicera", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()
    if _action_available(page, "Publicera version"):
        raise RuntimeError("Publish action still available after publishing.")


def _rollback(page: object, *, base_url: str, archived_version_id: str) -> None:
    page.goto(
        f"{base_url}/admin/tool-versions/{archived_version_id}", wait_until="domcontentloaded"
    )
    _select_action(page, "Återställ version")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name=re.compile(r"Återställ", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()
    page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-11-16-editor-workflow-actions")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _open_editor(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _ensure_draft(page)
        page.screenshot(path=str(artifacts_dir / "draft-ready.png"), full_page=True)

        _submit_for_review(page, note="Redo för granskning.")
        page.screenshot(path=str(artifacts_dir / "in-review.png"), full_page=True)

        _request_changes(page, message="Behöver justeras.")
        page.screenshot(path=str(artifacts_dir / "changes-requested.png"), full_page=True)

        second_review_id = _submit_for_review(page, note=None)
        page.screenshot(path=str(artifacts_dir / "review-again.png"), full_page=True)

        _publish(page, summary="Publiceringstest.")
        page.screenshot(path=str(artifacts_dir / "published.png"), full_page=True)

        _rollback(page, base_url=base_url, archived_version_id=second_review_id)
        page.screenshot(path=str(artifacts_dir / "rollback-complete.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
