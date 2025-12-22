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
        expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()

        # Browse -> pick the demo tool
        page.goto(f"{base_url}/browse/gemensamt/ovrigt", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))).to_be_visible()

        tool_row = page.locator("li").filter(has_text="Demo: Interaktiv")
        expect(tool_row).to_have_count(1)
        tool_row.get_by_role("link", name=re.compile(r"Koer|Kör", re.IGNORECASE)).click()
        page.wait_for_url("**/tools/demo-next-actions/run", wait_until="domcontentloaded")

        # Upload + run
        expect(page.get_by_role("heading", name=re.compile(r"Demo: Interaktiv", re.IGNORECASE))).to_be_visible()
        page.locator("input[type='file']").set_input_files(str(sample_file))
        page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()

        page.wait_for_url("**/tools/demo-next-actions/runs/**", wait_until="domcontentloaded")
        expect(page.get_by_text("Resultat")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "run-0.png"), full_page=True)

        # Download first artifact
        with page.expect_download() as download_info:
            page.locator("a[download]").first.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "artifact-0.bin"))

        reset_button = page.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE))
        if reset_button.count() == 0:
            raise RuntimeError(
                "Expected 'Nollställ' next_action to be available. "
                "Re-seed the script bank tool with updated code (seed-script-bank --sync-code)."
            )

        old_url = page.url
        reset_button.first.click()
        page.wait_for_function("oldUrl => window.location.href !== oldUrl", arg=old_url)
        expect(page.get_by_text("Resultat")).to_be_visible(timeout=60_000)
        expect(page.get_by_text(re.compile(r"Steg\s*=\s*0", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "run-reset.png"), full_page=True)

        # Run next_actions loop until actions disappear (max 5 turns as safety)
        for step in range(1, 6):
            next_step_button = page.get_by_role("button", name=re.compile(r"Nästa steg", re.IGNORECASE))
            if next_step_button.count() == 0:
                break

            note_field = page.get_by_label(re.compile(r"Anteckning", re.IGNORECASE)).first
            note_field.fill(f"step {step}")

            old_url = page.url
            next_step_button.click()
            page.wait_for_function("oldUrl => window.location.href !== oldUrl", arg=old_url)
            expect(page.get_by_text("Resultat")).to_be_visible(timeout=60_000)
            expect(
                page.get_by_text(re.compile(rf"Steg\s*=\s*{step}", re.IGNORECASE))
            ).to_be_visible(timeout=60_000)
            page.screenshot(path=str(artifacts_dir / f"run-{step}.png"), full_page=True)

            if step == 1:
                with page.expect_download() as download_info_step:
                    page.locator("a[download]").first.click()
                download_step = download_info_step.value
                download_step.save_as(str(artifacts_dir / "artifact-1.bin"))

        expect(page.get_by_role("button", name=re.compile(r"Nästa steg", re.IGNORECASE))).to_have_count(0)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
