"""Playwright E2E test for editor sandbox next_actions (ST-14-03).

Tests the SandboxRunner component's support for multi-step tools:
1. Initial run shows next_actions buttons
2. Submit action triggers new run
3. Step history UI appears and allows viewing previous steps
"""

from __future__ import annotations

import json
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


def _ensure_draft_for_tool(
    context: object,
    page: object,
    *,
    base_url: str,
    tool_slug: str,
    artifacts_dir: Path,
) -> str:
    """Ensure a draft version exists for the tool and navigate to editor.

    Returns the version_id of the draft.
    """
    # Get CSRF token
    csrf = context.request.get(f"{base_url}/api/v1/auth/csrf")
    csrf_token = csrf.json()["csrf_token"]

    # Get tool ID
    tool = context.request.get(f"{base_url}/api/v1/tools/{tool_slug}")
    tool_data = tool.json()
    tool_id = tool_data["id"]

    # Create or get draft
    draft = context.request.post(
        f"{base_url}/api/v1/editor/tools/{tool_id}/draft",
        headers={
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token,
        },
        data=json.dumps(
            {
                "source_code": None,  # Use existing source
                "entrypoint": None,
                "change_summary": "playwright e2e: sandbox next_actions test",
            }
        ),
    )
    draft_payload = draft.json()
    redirect_url = draft_payload["redirect_url"]
    version_id = redirect_url.split("/admin/tool-versions/")[-1].split("?")[0]

    # Navigate to editor
    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"Testa i sandbox", re.IGNORECASE))
    ).to_be_visible(timeout=30_000)

    page.screenshot(path=str(artifacts_dir / "editor-ready.png"), full_page=True)
    return version_id


def _run_sandbox(page: object, *, sample_file: Path, artifacts_dir: Path) -> None:
    """Upload file and run sandbox, wait for completion."""
    file_input = page.locator("input[type='file']")
    expect(file_input).to_have_count(1, timeout=30_000)
    file_input.set_input_files(str(sample_file))

    page.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).click()

    # Wait for success
    expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(timeout=60_000)
    page.screenshot(path=str(artifacts_dir / "initial-run.png"), full_page=True)


def _get_sandbox_section(page: object) -> object:
    """Get the sandbox section of the page."""
    return page.get_by_text("Testfiler").locator(
        "xpath=ancestor::div[contains(@class,'space-y-4')][1]"
    )


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-14-03-editor-sandbox-next-actions-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create sample file
    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Testfil för sandbox next_actions.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
        )
        page = context.new_page()

        page.on("pageerror", lambda error: print(f"[pageerror] {error}"))
        page.on(
            "console",
            lambda message: print(
                f"[console:{message.type}] {message.text}"
                if message.type in {"warning", "error"}
                else f"[console] {message.text}"
            ),
        )

        # Login
        _login(page, base_url=base_url, email=email, password=password)
        print(f"Logged in. Current URL: {page.url}")

        # Navigate to editor for demo-next-actions tool
        _ensure_draft_for_tool(
            context,
            page,
            base_url=base_url,
            tool_slug="demo-next-actions",
            artifacts_dir=artifacts_dir,
        )

        # Run initial sandbox
        _run_sandbox(page, sample_file=sample_file, artifacts_dir=artifacts_dir)

        sandbox = _get_sandbox_section(page)

        # Verify next_actions buttons appear
        next_step_btn = sandbox.get_by_role("button", name=re.compile(r"Nästa steg", re.IGNORECASE))
        reset_btn = sandbox.get_by_role("button", name=re.compile(r"Nollställ", re.IGNORECASE))
        finish_btn = sandbox.get_by_role("button", name=re.compile(r"Avsluta", re.IGNORECASE))

        expect(next_step_btn).to_be_visible(timeout=10_000)
        expect(reset_btn).to_be_visible(timeout=10_000)
        expect(finish_btn).to_be_visible(timeout=10_000)
        print("Initial run complete: next_actions buttons visible.")

        # Fill in the note field and submit "Nästa steg"
        note_field = sandbox.get_by_label(re.compile(r"Anteckning", re.IGNORECASE)).first
        note_field.fill("steg 1 anteckning")

        next_step_btn.click()

        # Wait for new run to complete
        expect(sandbox.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )

        # Verify step output shows Steg = 1
        expect(sandbox.get_by_text(re.compile(r"Steg\s*=\s*1", re.IGNORECASE))).to_be_visible(
            timeout=10_000
        )
        page.screenshot(path=str(artifacts_dir / "after-step-1.png"), full_page=True)
        print("Step 1 complete: output shows Steg = 1.")

        # Verify step history UI appears
        step1_btn = sandbox.get_by_role("button", name=re.compile(r"^Steg\s*1$", re.IGNORECASE))
        aktuellt_btn = sandbox.get_by_role("button", name=re.compile(r"Aktuellt", re.IGNORECASE))

        expect(step1_btn).to_be_visible(timeout=10_000)
        expect(aktuellt_btn).to_be_visible(timeout=10_000)
        print("Step history UI visible: Steg 1 and Aktuellt buttons present.")

        # Click Steg 1 to view previous step
        step1_btn.click()

        # Verify we see step 0 output (initial run)
        expect(sandbox.get_by_text(re.compile(r"Steg\s*=\s*0", re.IGNORECASE))).to_be_visible(
            timeout=10_000
        )
        page.screenshot(path=str(artifacts_dir / "step-history-selected.png"), full_page=True)
        print("Viewing step 1 history: output shows Steg = 0.")

        # Click Aktuellt to return to current
        aktuellt_btn.click()

        # Verify we see step 1 output again
        expect(sandbox.get_by_text(re.compile(r"Steg\s*=\s*1", re.IGNORECASE))).to_be_visible(
            timeout=10_000
        )
        print("Returned to current: output shows Steg = 1.")

        # Clear and run new file to verify step history clears
        clear_btn = sandbox.get_by_role("button", name=re.compile(r"Rensa", re.IGNORECASE))
        if clear_btn.count() > 0 and clear_btn.is_visible():
            clear_btn.click()

            # Run again
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(str(sample_file))
            page.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).click()

            expect(sandbox.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
                timeout=60_000
            )

            # Verify step history is cleared (no Steg 1 button)
            step1_btn_after = sandbox.get_by_role(
                "button", name=re.compile(r"^Steg\s*1$", re.IGNORECASE)
            )
            expect(step1_btn_after).to_have_count(0, timeout=5_000)
            print("New run clears step history: no Steg 1 button.")

        page.screenshot(path=str(artifacts_dir / "test-complete.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")
    print("ST-14-03 Editor Sandbox next_actions E2E test passed!")


if __name__ == "__main__":
    main()
