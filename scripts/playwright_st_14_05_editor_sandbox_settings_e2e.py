"""Playwright E2E test for editor sandbox settings panel (ST-14-05).

Verifies that:
- Editor sandbox shows the per-user settings panel for a draft version
- Saving settings persists and affects sandbox runs (SKRIPTOTEKET_MEMORY_PATH injection)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

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
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible()
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def _ensure_draft_for_tool(
    context: object,
    page: object,
    *,
    base_url: str,
    tool_slug: str,
    artifacts_dir: Path,
) -> tuple[str, str]:
    """Ensure a draft version exists for the tool and navigate to editor."""
    csrf = context.request.get(f"{base_url}/api/v1/auth/csrf")
    expect(csrf).to_be_ok()
    csrf_token = csrf.json()["csrf_token"]

    tool = context.request.get(f"{base_url}/api/v1/tools/{tool_slug}")
    expect(tool).to_be_ok()
    tool_id = tool.json()["id"]

    boot = context.request.get(f"{base_url}/api/v1/editor/tools/{tool_id}")
    expect(boot).to_be_ok()
    boot_payload = boot.json()
    entrypoint = str(boot_payload.get("entrypoint") or "run_tool")
    source_code = str(boot_payload.get("source_code") or "")

    draft_head_id = boot_payload.get("draft_head_id")
    if draft_head_id:
        lock = context.request.post(
            f"{base_url}/api/v1/editor/tools/{tool_id}/draft-lock",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token,
            },
            data=json.dumps({"draft_head_id": draft_head_id, "force": False}),
        )
        expect(lock).to_be_ok()

    draft = context.request.post(
        f"{base_url}/api/v1/editor/tools/{tool_id}/draft",
        headers={
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token,
        },
        data=json.dumps(
            {
                "source_code": source_code,
                "entrypoint": entrypoint,
                "settings_schema": boot_payload.get("settings_schema"),
                "input_schema": boot_payload.get("input_schema"),
                "usage_instructions": boot_payload.get("usage_instructions"),
                "change_summary": "playwright e2e: editor sandbox settings panel",
                "derived_from_version_id": boot_payload.get("derived_from_version_id"),
            }
        ),
    )
    expect(draft).to_be_ok()
    redirect_url = draft.json()["redirect_url"]
    version_id = redirect_url.split("/admin/tool-versions/")[-1].split("?")[0]

    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    expect(
        page.get_by_role(
            "heading",
            name=re.compile(r"(Testkör kod|Testkor kod|Källkod|Kallkod)", re.IGNORECASE),
        ).first
    ).to_be_visible(timeout=30_000)

    page.screenshot(path=str(artifacts_dir / "editor-ready.png"), full_page=True)
    return tool_id, version_id


def _get_sandbox_input_panel(page: object) -> object:
    inputs_summary = page.locator(
        "summary", has_text=re.compile(r"Indata\s*\(JSON\)", re.IGNORECASE)
    ).first
    return inputs_summary.locator("xpath=ancestor::div[contains(@class,'space-y-4')][1]")


def _get_settings_panel(page: object) -> object:
    return page.get_by_role("heading", name=re.compile(r"^Inställningar$", re.IGNORECASE)).locator(
        "xpath=ancestor::div[contains(@class,'border')][1]"
    )


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-14-05-editor-sandbox-settings-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("ST-14-05 editor sandbox settings e2e.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
        )
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)
        tool_slug = "demo-settings-test"
        tool_id, _ = _ensure_draft_for_tool(
            context,
            page,
            base_url=base_url,
            tool_slug=tool_slug,
            artifacts_dir=artifacts_dir,
        )

        sandbox_input = _get_sandbox_input_panel(page)
        settings_panel = _get_settings_panel(page)
        sandbox_theme = f"sandbox-{uuid4().hex[:8]}"

        # Open settings panel and configure theme_color
        settings_toggle = settings_panel.get_by_role(
            "button", name=re.compile(r"^(Visa|Dölj)$", re.IGNORECASE)
        ).first
        expect(settings_toggle).to_be_visible(timeout=20_000)
        settings_toggle.click()

        theme_field = settings_panel.get_by_label("Färgtema").first
        expect(theme_field).to_be_visible()
        theme_field.fill(sandbox_theme)

        save_settings = settings_panel.get_by_role(
            "button", name=re.compile(r"^Spara$", re.IGNORECASE)
        ).first
        save_settings.click()
        expect(page.get_by_text("Inställningar sparade.")).to_be_visible(timeout=20_000)
        page.screenshot(path=str(artifacts_dir / "settings-saved.png"), full_page=True)

        # Run sandbox and verify settings are injected
        file_input = sandbox_input.locator("input[type='file']")
        expect(file_input).to_have_count(1, timeout=30_000)
        file_input.set_input_files(str(sample_file))

        sandbox_input.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).click()
        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        expect(page.get_by_text(f"theme_color={sandbox_theme}")).to_be_visible(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "run-with-settings.png"), full_page=True)

        # Verify settings persistence after reload
        page.reload(wait_until="domcontentloaded")
        settings_panel = _get_settings_panel(page)
        settings_panel.get_by_role(
            "button", name=re.compile(r"^(Visa|Dölj)$", re.IGNORECASE)
        ).first.click()
        expect(settings_panel.get_by_label("Färgtema").first).to_have_value(sandbox_theme)
        page.screenshot(path=str(artifacts_dir / "settings-persisted.png"), full_page=True)

        # Verify sandbox settings did not leak into production settings context
        settings_response = context.request.get(f"{base_url}/api/v1/tools/{tool_id}/settings")
        expect(settings_response).to_be_ok()
        production_values = settings_response.json().get("values", {})
        if production_values.get("theme_color") == sandbox_theme:
            raise RuntimeError("Sandbox settings leaked into production settings context.")

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
