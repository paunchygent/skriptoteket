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
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    try:
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible(timeout=10_000)
    except AssertionError:
        page.screenshot(path=str(artifacts_dir / "login-failure.png"), full_page=True)
        raise


def _create_draft_tool(page: object, *, base_url: str, title: str) -> str:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Verktyg (admin)")).to_be_visible()

    page.get_by_role("button", name="Skapa nytt verktyg").click()
    dialog = page.get_by_role("dialog", name="Skapa nytt verktyg")
    expect(dialog).to_be_visible()

    dialog.get_by_label("Titel").fill(title)
    dialog.get_by_role("button", name="Skapa").click()

    page.wait_for_url("**/admin/tools/**", wait_until="domcontentloaded")
    match = re.search(r"/admin/tools/([0-9a-f-]{36})$", page.url)
    if not match:
        raise RuntimeError(f"Could not extract tool_id from URL: {page.url}")
    return match.group(1)


def _open_metadata_drawer(page: object) -> object:
    page.get_by_role("button", name="Metadata").click()
    drawer = page.get_by_role("dialog", name="Redigera metadata")
    expect(drawer).to_be_visible()
    return drawer


def _publish_active_version(page: object, artifacts_dir: Path) -> None:
    page.get_by_role("button", name="Spara").click()
    page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")
    page.screenshot(path=str(artifacts_dir / "draft-version-created.png"), full_page=True)

    page.get_by_role("button", name="Begär publicering").click()
    modal = page.get_by_role("dialog")
    expect(modal).to_be_visible()
    modal.get_by_role("button", name="Begär publicering").click()
    expect(page.get_by_text("Begär publicering skickad.")).to_be_visible(timeout=10_000)

    page.get_by_role("button", name="Publicera version").click()
    modal = page.get_by_role("dialog")
    expect(modal).to_be_visible()
    modal.get_by_role("button", name="Publicera").click()
    expect(page.get_by_text("Version publicerad.")).to_be_visible(timeout=10_000)
    page.screenshot(path=str(artifacts_dir / "version-published.png"), full_page=True)


def _publish_tool_from_admin_list(page: object, *, base_url: str, title: str) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
    row = page.locator("li", has_text=title).first
    expect(row).to_be_visible()
    row.get_by_role("switch").click()


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-admin-tool-authoring")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    title = "ÅÄÖ matteprov"

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

        tool_id = _create_draft_tool(page, base_url=base_url, title=title)
        expect(page.get_by_text(f"draft-{tool_id}")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "draft-tool-editor.png"), full_page=True)

        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        row = page.locator("li", has_text=title).first
        expect(row.get_by_text("Ingen kod")).to_be_visible()
        expect(row.get_by_text(f"draft-{tool_id}")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "admin-tools-in-progress.png"), full_page=True)

        row.get_by_role("link", name=re.compile(r"Redigera", re.IGNORECASE)).click()
        page.wait_for_url("**/admin/tools/**", wait_until="domcontentloaded")

        _publish_active_version(page, artifacts_dir)

        _publish_tool_from_admin_list(page, base_url=base_url, title=title)
        expect(
            page.get_by_text("Slug måste ändras (får inte börja med 'draft-') innan publicering.")
        ).to_be_visible(timeout=10_000)
        page.screenshot(
            path=str(artifacts_dir / "publish-blocked-placeholder-slug.png"), full_page=True
        )

        page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
        drawer = _open_metadata_drawer(page)
        drawer.get_by_placeholder("t.ex. mattest").fill("ogiltig slug!!")
        drawer.get_by_role("button", name="Spara metadata").click()
        expect(drawer.get_by_text("Ogiltig slug.")).to_be_visible(timeout=10_000)

        drawer.get_by_role("button", name="Använd nuvarande titel").click()
        drawer.get_by_role("button", name="Spara metadata").click()
        expect(drawer.get_by_text("Slug sparad.")).to_be_visible(timeout=10_000)
        page.screenshot(path=str(artifacts_dir / "slug-updated.png"), full_page=True)

        _publish_tool_from_admin_list(page, base_url=base_url, title=title)
        expect(
            page.get_by_text("Välj minst ett yrke och minst en kategori innan publicering.")
        ).to_be_visible(timeout=10_000)
        page.screenshot(
            path=str(artifacts_dir / "publish-blocked-missing-taxonomy.png"), full_page=True
        )

        page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
        drawer = _open_metadata_drawer(page)
        profession_checkbox = drawer.locator(
            "xpath=//span[normalize-space()='Yrken']/ancestor::div[contains(@class,'space-y-2')][1]//input[@type='checkbox']"
        ).first
        category_checkbox = drawer.locator(
            "xpath=//span[normalize-space()='Kategorier']/ancestor::div[contains(@class,'space-y-2')][1]//input[@type='checkbox']"
        ).first

        expect(profession_checkbox).to_be_visible()
        expect(category_checkbox).to_be_visible()
        profession_checkbox.check()
        category_checkbox.check()

        drawer.get_by_role("button", name="Spara metadata").click()
        expect(drawer.get_by_text("Taxonomi sparad.")).to_be_visible(timeout=10_000)
        page.screenshot(path=str(artifacts_dir / "taxonomy-saved.png"), full_page=True)

        _publish_tool_from_admin_list(page, base_url=base_url, title=title)
        expect(page.get_by_text(re.compile(r"har publicerats", re.IGNORECASE))).to_be_visible(
            timeout=10_000
        )
        page.screenshot(path=str(artifacts_dir / "tool-published.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
