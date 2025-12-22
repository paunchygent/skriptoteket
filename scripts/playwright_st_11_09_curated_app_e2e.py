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


def _extract_run_id(text: str) -> str:
    match = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text, re.IGNORECASE
    )
    if not match:
        raise RuntimeError(f"Could not extract run_id from text: {text}")
    return match.group(0)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-11-09-curated-app-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
        )
        page = context.new_page()

        # Login (SPA)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible()

        # Navigate to curated app via browse then deep-link to SPA route
        page.goto(f"{base_url}/browse/gemensamt/ovrigt", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))
        ).to_be_visible()
        page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")

        expect(
            page.get_by_role("heading", name=re.compile(r"Interaktiv räknare", re.IGNORECASE))
        ).to_be_visible()
        expect(page.get_by_text(re.compile(r"Kurerad app", re.IGNORECASE))).to_be_visible()

        # Start app (action_id=start) if no existing run
        start_button = page.get_by_role("button", name=re.compile(r"Starta", re.IGNORECASE))
        result_heading = page.get_by_text(re.compile(r"Resultat", re.IGNORECASE))

        try:
            expect(result_heading).to_be_visible(timeout=15_000)
        except AssertionError:
            # Maybe needs an explicit start
            if start_button.count() == 0:
                page.screenshot(path=str(artifacts_dir / "00-no-start.png"), full_page=True)
                raise

        if start_button.count() > 0:
            start_button.click()
            expect(result_heading).to_be_visible(timeout=30_000)

        run_id_locator = page.get_by_text(
            re.compile(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
            )
        ).first
        run_id_locator.wait_for(state="visible", timeout=30_000)
        initial_run_id = _extract_run_id(run_id_locator.inner_text())
        print(f"Initial run ID: {initial_run_id}")
        page.screenshot(path=str(artifacts_dir / "01-start.png"), full_page=True)

        # Increment with step=2
        step_field = page.get_by_label(re.compile(r"Steg", re.IGNORECASE)).first
        step_field.fill("2")
        page.get_by_role("button", name=re.compile(r"Öka", re.IGNORECASE)).click()

        expect(page.get_by_text(re.compile(r"Resultat", re.IGNORECASE))).to_be_visible(
            timeout=30_000
        )
        run_id_after_increment = _extract_run_id(run_id_locator.inner_text())
        print(f"After increment run ID: {run_id_after_increment}")
        page.screenshot(path=str(artifacts_dir / "02-increment.png"), full_page=True)

        # Reset
        page.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Resultat", re.IGNORECASE))).to_be_visible(
            timeout=30_000
        )
        run_id_after_reset = _extract_run_id(run_id_locator.inner_text())
        print(f"After reset run ID: {run_id_after_reset}")
        page.screenshot(path=str(artifacts_dir / "03-reset.png"), full_page=True)

        # Export artifact (action_id=export)
        page.get_by_role("button", name=re.compile(r"Spara som fil", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Filer", re.IGNORECASE))).to_be_visible(timeout=30_000)
        download_link = page.locator("a[download]").first
        expect(download_link).to_be_visible(timeout=30_000)
        with page.expect_download() as download_info:
            download_link.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "counter.txt"))
        run_id_after_export = _extract_run_id(run_id_locator.inner_text())
        print(f"After export run ID: {run_id_after_export}")
        page.screenshot(path=str(artifacts_dir / "04-export.png"), full_page=True)

        # Capture run_id and verify replay after reload
        run_id = _extract_run_id(run_id_locator.inner_text())

        page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
        expect(page.get_by_text(run_id)).to_be_visible(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "05-reload.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
