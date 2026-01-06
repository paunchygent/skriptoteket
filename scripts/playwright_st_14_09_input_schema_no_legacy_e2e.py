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


def _assert_tool_run_file_picker(
    page: object,
    *,
    base_url: str,
    tool_slug: str,
    expect_file_input: bool,
    artifacts_dir: Path,
    screenshot_name: str,
) -> None:
    page.goto(f"{base_url}/tools/{tool_slug}/run", wait_until="domcontentloaded")
    expect(page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )

    file_input = page.locator("input[type='file']")
    expect(file_input).to_have_count(1 if expect_file_input else 0, timeout=30_000)
    page.screenshot(path=str(artifacts_dir / screenshot_name), full_page=True)


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
                "change_summary": "playwright e2e: st-14-09 input schema no legacy null",
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


def _get_sandbox_input_panel(page: object) -> object:
    inputs_summary = page.locator(
        "summary", has_text=re.compile(r"Indata\\s*\\(JSON\\)", re.IGNORECASE)
    ).first
    return inputs_summary.locator("xpath=ancestor::div[contains(@class,'space-y-4')][1]")


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-09-input-schema-no-legacy-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=False,
        )
        page = context.new_page()

        _login(page, base_url=base_url, email=config.email, password=config.password)

        _assert_tool_run_file_picker(
            page,
            base_url=base_url,
            tool_slug="demo-inputs",
            expect_file_input=False,
            artifacts_dir=artifacts_dir,
            screenshot_name="runtime-demo-inputs-no-file-picker.png",
        )
        _assert_tool_run_file_picker(
            page,
            base_url=base_url,
            tool_slug="demo-inputs-file",
            expect_file_input=True,
            artifacts_dir=artifacts_dir,
            screenshot_name="runtime-demo-inputs-file-has-file-picker.png",
        )

        _ensure_draft_for_tool(context, page, base_url=base_url, tool_slug="demo-inputs-file")
        input_schema_editor = page.locator("#tool-input-schema")
        expect(input_schema_editor).to_be_visible(timeout=30_000)

        save_button = page.get_by_role(
            "button",
            name=re.compile(r"^(Spara|Skapa ny) arbetsversion$", re.IGNORECASE),
        ).first
        expect(save_button).to_be_visible(timeout=30_000)
        expect(save_button).to_be_enabled(timeout=30_000)

        page.screenshot(path=str(artifacts_dir / "editor-before-clear.png"), full_page=True)

        input_schema_editor.fill("[")
        expect(save_button).to_be_disabled(timeout=30_000)
        input_schema_error = input_schema_editor.locator("xpath=following-sibling::p[1]")
        expect(input_schema_error).to_be_visible(timeout=30_000)
        expect(input_schema_error).to_contain_text(re.compile(r"giltig\s+JSON", re.IGNORECASE))
        page.screenshot(
            path=str(artifacts_dir / "editor-invalid-json-blocks-save.png"), full_page=True
        )

        input_schema_editor.fill("")
        expect(save_button).to_be_enabled(timeout=30_000)

        save_button.click()
        expect(input_schema_editor).to_have_value("[]", timeout=30_000)

        sandbox_input = _get_sandbox_input_panel(page)
        expect(sandbox_input.locator("input[type='file']")).to_have_count(0, timeout=30_000)
        page.screenshot(
            path=str(artifacts_dir / "editor-after-clear-no-file-picker.png"), full_page=True
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
