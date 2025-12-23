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


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def _run_curated_app(page: object, *, base_url: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"Interaktiv.*räknare", re.IGNORECASE))
    ).to_be_visible()
    expect(page.get_by_text(re.compile(r"Kurerad app", re.IGNORECASE))).to_be_visible()

    start_button = page.get_by_role("button", name=re.compile(r"Starta", re.IGNORECASE))
    if start_button.count() > 0 and start_button.is_visible():
        start_button.click()

    action_button = page.get_by_role("button", name=re.compile(r"Öka", re.IGNORECASE))
    if action_button.count() > 0:
        expect(action_button).to_be_visible(timeout=60_000)
    else:
        expect(
            page.get_by_text(re.compile(r"(Pågår|Lyckades|Misslyckades|Tidsgräns)", re.IGNORECASE))
        ).to_be_visible(timeout=60_000)
    page.screenshot(path=str(artifacts_dir / "curated-app.png"), full_page=True)


def _run_demo_tool(page: object, *, base_url: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/browse/gemensamt/ovrigt", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))
    ).to_be_visible()

    tool_row = page.locator("li").filter(has_text="Demo: Interaktiv")
    expect(tool_row).to_have_count(1)
    tool_row.get_by_role("link", name=re.compile(r"Välj", re.IGNORECASE)).click()
    page.wait_for_url("**/tools/**/run", wait_until="domcontentloaded")

    expect(
        page.get_by_role("heading", name=re.compile(r"Demo: Interaktiv", re.IGNORECASE))
    ).to_be_visible()

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hello from Playwright runtime smoke.\n", encoding="utf-8")
    page.locator("input[type='file']").set_input_files(str(sample_file))
    page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()

    expect(page.get_by_role("button", name=re.compile(r"Rensa", re.IGNORECASE))).to_be_visible(
        timeout=60_000
    )
    page.screenshot(path=str(artifacts_dir / "tool-run.png"), full_page=True)

    download_link = page.locator("a[download]").first
    if download_link.count() > 0:
        with page.expect_download() as download_info:
            download_link.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "artifact-0.bin"))


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-runtime-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        _run_curated_app(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _run_demo_tool(page, base_url=base_url, artifacts_dir=artifacts_dir)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
