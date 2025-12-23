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

    artifacts_dir = Path(".artifacts/st-11-07-spa-tool-run-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hej!\nDet här är en demo för next_actions.\n", encoding="utf-8")

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

        # Navigate directly to the demo tool run page (SPA stays on same URL)
        page.goto(f"{base_url}/tools/demo-next-actions/run", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Demo: Interaktiv", re.IGNORECASE))
        ).to_be_visible()

        # Upload file and run
        page.locator("input[type='file']").set_input_files(str(sample_file))
        page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()

        # Wait for results to appear (SPA shows results inline, no URL change)
        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "run-0.png"), full_page=True)

        # Check for artifacts and download first one
        download_links = page.locator("a[download]")
        if download_links.count() > 0:
            with page.expect_download() as download_info:
                download_links.first.click()
            download = download_info.value
            download.save_as(str(artifacts_dir / "artifact-0.bin"))

        # Check for next actions (multi-step tool)
        reset_button = page.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE))
        if reset_button.count() == 0:
            print("No 'Nollställ' action available - tool may not support next_actions.")
            context.close()
            browser.close()
            print(f"Playwright artifacts written to: {artifacts_dir}")
            return

        # Click reset action and wait for new results
        reset_button.first.click()
        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        expect(page.get_by_text(re.compile(r"Steg\s*=\s*0", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "run-reset.png"), full_page=True)

        # Run next_actions loop until actions disappear (max 5 turns as safety)
        for step in range(1, 6):
            next_step_button = page.get_by_role(
                "button", name=re.compile(r"Nästa steg", re.IGNORECASE)
            )
            if next_step_button.count() == 0:
                break

            note_field = page.get_by_label(re.compile(r"Anteckning", re.IGNORECASE)).first
            note_field.fill(f"step {step}")

            next_step_button.click()
            expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
                timeout=60_000
            )
            expect(
                page.get_by_text(re.compile(rf"Steg\s*=\s*{step}", re.IGNORECASE))
            ).to_be_visible(timeout=60_000)
            page.screenshot(path=str(artifacts_dir / f"run-{step}.png"), full_page=True)

            if step == 1:
                download_links = page.locator("a[download]")
                if download_links.count() > 0:
                    with page.expect_download() as download_info_step:
                        download_links.first.click()
                    download_step = download_info_step.value
                    download_step.save_as(str(artifacts_dir / "artifact-1.bin"))

        expect(
            page.get_by_role("button", name=re.compile(r"Nästa steg", re.IGNORECASE))
        ).to_have_count(0)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
