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


def _extract_uuid_from_url(url: str) -> str:
    match = re.search(r"/runs/([0-9a-f-]{36})$", url, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"Failed to extract run_id from URL: {url}")
    return match.group(1)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-11-08-spa-my-runs-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hej!\nDet här är en demo för my-runs.\n", encoding="utf-8")

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

        # Create a run (via tool run flow) so /my-runs has something to list.
        page.goto(f"{base_url}/browse/gemensamt/ovrigt", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Övrigt", re.IGNORECASE))).to_be_visible()

        tool_row = page.locator("li").filter(has_text="Demo: Interaktiv")
        expect(tool_row).to_have_count(1)
        tool_row.get_by_role("link", name=re.compile(r"Koer|Kör", re.IGNORECASE)).click()
        page.wait_for_url("**/tools/demo-next-actions/run", wait_until="domcontentloaded")

        page.locator("input[type='file']").set_input_files(str(sample_file))
        page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()
        page.wait_for_url("**/tools/demo-next-actions/runs/**", wait_until="domcontentloaded")
        expect(page.get_by_text("Fortsätt")).to_be_visible()

        created_run_id = _extract_uuid_from_url(page.url)
        page.screenshot(path=str(artifacts_dir / "tool-result.png"), full_page=True)

        # My runs list -> open that run
        page.goto(f"{base_url}/my-runs", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Mina körningar", re.IGNORECASE))).to_be_visible()

        run_row = page.locator("li").filter(has_text=created_run_id)
        expect(run_row).to_have_count(1)
        run_row.get_by_role("link", name=re.compile(r"Öppna", re.IGNORECASE)).click()

        page.wait_for_url(f"**/my-runs/{created_run_id}", wait_until="domcontentloaded")
        expect(page.get_by_text("Resultat")).to_be_visible(timeout=60_000)
        page.screenshot(path=str(artifacts_dir / "my-runs-detail-0.png"), full_page=True)

        # Download first artifact from my-runs detail
        with page.expect_download() as download_info:
            page.locator("a[download]").first.click()
        download = download_info.value
        download.save_as(str(artifacts_dir / "artifact-0.bin"))

        # Prove next_actions works from my-runs detail by resetting + stepping
        reset_button = page.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE))
        expect(reset_button).to_have_count(1)

        old_url = page.url
        reset_button.click()
        page.wait_for_function("oldUrl => window.location.href !== oldUrl", arg=old_url)
        expect(page.get_by_text("Resultat")).to_be_visible(timeout=60_000)
        expect(page.get_by_text(re.compile(r"Steg\s*=\s*0", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "my-runs-detail-reset.png"), full_page=True)

        # Step forward once
        note_field = page.get_by_label(re.compile(r"Anteckning", re.IGNORECASE)).first
        note_field.fill("from my-runs")

        next_step_button = page.get_by_role("button", name=re.compile(r"Nästa steg", re.IGNORECASE))
        expect(next_step_button).to_have_count(1)

        old_url = page.url
        next_step_button.click()
        page.wait_for_function("oldUrl => window.location.href !== oldUrl", arg=old_url)
        expect(page.get_by_text("Resultat")).to_be_visible(timeout=60_000)
        expect(page.get_by_text(re.compile(r"Steg\s*=\s*1", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "my-runs-detail-step-1.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
