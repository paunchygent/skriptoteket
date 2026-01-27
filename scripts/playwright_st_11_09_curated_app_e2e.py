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
        dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
        expect(dialog).to_be_visible()
        dialog.get_by_label("E-post").fill(email)
        dialog.get_by_label("Lösenord").fill(password)
        dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible()

        # Navigate to curated app via browse then deep-link to SPA route
        page.goto(f"{base_url}/browse/professions/gemensamt/ovrigt", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))
        ).to_be_visible()
        page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")

        expect(
            page.get_by_role("heading", name=re.compile(r"Interaktiv räknare", re.IGNORECASE))
        ).to_be_visible()
        expect(page.get_by_text(re.compile(r"Kurerad app", re.IGNORECASE))).to_be_visible()

        # Start app (action_id=start) if needed.
        # AppHostView -> AppDetailView means the Start button may appear a moment after route load.
        start_button = page.get_by_role("button", name=re.compile(r"Starta", re.IGNORECASE))
        counter_notice = page.get_by_text(re.compile(r"Räknare:\s*\d+", re.IGNORECASE)).first

        try:
            expect(counter_notice).to_be_visible(timeout=15_000)
        except AssertionError:
            expect(start_button).to_be_visible(timeout=15_000)
            start_button.click()
            expect(counter_notice).to_be_visible(timeout=30_000)

        # Reset then increment with step=2 (deterministic)
        page.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Räknare:\s*0\b", re.IGNORECASE))).to_be_visible(
            timeout=30_000
        )
        step_field = page.get_by_label(re.compile(r"Steg", re.IGNORECASE)).first
        step_field.fill("2")
        page.get_by_role("button", name=re.compile(r"Öka", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Räknare:\s*2\b", re.IGNORECASE))).to_be_visible(
            timeout=30_000
        )
        page.screenshot(path=str(artifacts_dir / "01-counter.png"), full_page=True)

        # Export artifact (action_id=export)
        page.get_by_role("button", name=re.compile(r"Spara som fil", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Filer", re.IGNORECASE))).to_be_visible(timeout=30_000)
        download_link = page.locator("a[download]").first
        expect(download_link).to_be_visible(timeout=30_000)
        with page.expect_download() as download_info:
            download_link.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "counter.txt"))
        page.screenshot(path=str(artifacts_dir / "02-counter-export.png"), full_page=True)

        page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
        expect(page.get_by_text(re.compile(r"Räknare:\s*2\b", re.IGNORECASE))).to_be_visible(
            timeout=30_000
        )
        page.screenshot(path=str(artifacts_dir / "03-counter-reload.png"), full_page=True)

        # Navigate to bespoke curated app (Reagensberedning)
        page.goto(f"{base_url}/browse/professions/larare/ovrigt", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))
        ).to_be_visible()

        page.goto(f"{base_url}/apps/chemistry.reagent_prep_chef", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Reagensberedning", re.IGNORECASE))
        ).to_be_visible()

        formula_field = page.get_by_label(re.compile(r"Ämne.*formel", re.IGNORECASE))
        formula_field.fill("NaCl")
        page.get_by_role("button", name=re.compile(r"Beräkna", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Resultat", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "04-reagent-calc.png"), full_page=True)

        export_button = page.get_by_role("button", name=re.compile(r"Exportera PDF", re.IGNORECASE))
        expect(export_button).to_be_enabled(timeout=30_000)
        export_button.click()
        expect(page.get_by_text(re.compile(r"Filer", re.IGNORECASE))).to_be_visible(timeout=30_000)

        download_link = page.locator("a[download]").first
        expect(download_link).to_be_visible(timeout=30_000)
        with page.expect_download() as download_info:
            download_link.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "reagensberedning.pdf"))
        page.screenshot(path=str(artifacts_dir / "05-reagent-export.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
