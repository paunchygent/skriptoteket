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

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible(timeout=30_000)
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )


def _ensure_draft_for_tool(
    context: object,
    page: object,
    *,
    base_url: str,
    tool_slug: str,
) -> tuple[str, str]:
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
                "change_summary": "playwright e2e: st-14-16 schema validation errors ux",
                "derived_from_version_id": boot_payload.get("create_draft_from_version_id")
                or boot_payload.get("parent_version_id"),
            }
        ),
    )
    expect(draft).to_be_ok()
    redirect_url = draft.json()["redirect_url"]
    version_id = redirect_url.split("/admin/tool-versions/")[-1].split("?")[0]

    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    return tool_id, version_id


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-16-editor-schema-validation-errors-ux-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=False,
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

        _login(page, base_url=base_url, email=config.email, password=config.password)
        _ensure_draft_for_tool(context, page, base_url=base_url, tool_slug="demo-inputs-file")

        save_button = page.get_by_role(
            "button",
            name=re.compile(r"^(Spara|Skapa ny) arbetsversion$", re.IGNORECASE),
        ).first
        run_button = page.get_by_role(
            "button", name=re.compile(r"^Testkör kod$", re.IGNORECASE)
        ).first

        settings_schema_container = page.locator("#tool-settings-schema")
        input_schema_container = page.locator("#tool-input-schema")
        expect(settings_schema_container).to_be_visible(timeout=30_000)
        expect(input_schema_container).to_be_visible(timeout=30_000)
        expect(save_button).to_be_visible(timeout=30_000)
        expect(run_button).to_be_visible(timeout=30_000)

        settings_schema_editor = settings_schema_container.locator(".cm-content")
        input_schema_editor = input_schema_container.locator(".cm-content")
        expect(settings_schema_editor).to_be_visible(timeout=30_000)
        expect(input_schema_editor).to_be_visible(timeout=30_000)

        # Parseable, but backend-invalid settings_schema (missing required "name")
        settings_schema_editor.fill('[{"label":"Färgtema","kind":"string"}]')
        # Parseable, but backend-invalid input_schema (file.max exceeds UPLOAD_MAX_FILES=10)
        input_schema_editor.fill(
            '[{"name":"files","label":"Filer","kind":"file","min":0,"max":11}]'
        )

        settings_section = settings_schema_container.locator(
            "xpath=ancestor::div[contains(@class,'border-t')][1]"
        )
        input_section = input_schema_container.locator(
            "xpath=ancestor::div[contains(@class,'border-t')][1]"
        )
        settings_issue_heading = settings_section.get_by_text(
            re.compile(r"Valideringsfel", re.IGNORECASE)
        )
        input_issue_heading = input_section.get_by_text(
            re.compile(r"Valideringsfel", re.IGNORECASE)
        )

        expect(settings_issue_heading).to_be_visible(timeout=30_000)
        expect(settings_section).to_contain_text("/0/name", timeout=30_000)
        expect(input_issue_heading).to_be_visible(timeout=30_000)
        expect(input_section).to_contain_text("/0/max", timeout=30_000)

        expect(save_button).to_be_disabled(timeout=30_000)
        expect(run_button).to_be_disabled(timeout=30_000)
        page.screenshot(
            path=str(artifacts_dir / "invalid-schemas-block-save-run.png"), full_page=True
        )

        # Fix schemas -> issues clear -> actions re-enable
        settings_schema_editor.fill('[{"name":"theme_color","label":"Färgtema","kind":"string"}]')
        input_schema_editor.fill(
            '[{"name":"files","label":"Filer","kind":"file","min":0,"max":10}]'
        )

        expect(settings_issue_heading).to_have_count(0, timeout=30_000)
        expect(input_issue_heading).to_have_count(0, timeout=30_000)

        expect(save_button).to_be_enabled(timeout=30_000)
        expect(run_button).to_be_enabled(timeout=30_000)
        page.screenshot(
            path=str(artifacts_dir / "schemas-valid-actions-enabled.png"), full_page=True
        )

        dirty_badge = page.get_by_text(re.compile(r"Osparat", re.IGNORECASE)).first
        expect(dirty_badge).to_be_visible(timeout=30_000)

        save_button.click()
        expect(dirty_badge).to_have_count(0, timeout=30_000)
        expect(run_button).to_be_enabled(timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "after-save-run-enabled.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
