"""Playwright E2E: sandbox file_refs + session reuse validation.

Flow:
1) Open editor for demo-inputs-file via draft API.
2) Sandbox run with uploaded file and verify /work/input path in outputs.
3) Select saved file refs and rerun without upload, verify /work/input again.
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


def _log_unauthorized(response: object) -> None:
    try:
        if response.status == 401:
            print(f"[401] {response.url}")
    except Exception:
        return


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")

    logout_button = page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
    try:
        expect(logout_button).to_be_visible(timeout=2_000)
        return
    except AssertionError:
        pass

    login_modal = page.get_by_role("dialog")
    expect(login_modal).to_be_visible(timeout=30_000)
    login_modal.get_by_label("E-post").fill(email)
    login_modal.get_by_label("Lösenord").fill(password)
    login_modal.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(logout_button).to_be_visible(timeout=30_000)


def _ensure_draft_for_tool(
    context: object,
    page: object,
    *,
    base_url: str,
    tool_slug: str,
    artifacts_dir: Path,
) -> str:
    csrf_token = "huleedu-gateway-context"

    tool = context.request.get(f"{base_url}/api/v1/tools/{tool_slug}")
    if tool.status == 404:
        raise RuntimeError(
            f"Tool '{tool_slug}' not found. Seed via: pdm run seed-script-bank --slug {tool_slug}"
        )
    expect(tool).to_be_ok()
    tool_id = tool.json()["id"]

    boot = context.request.get(f"{base_url}/api/v1/editor/tools/{tool_id}")
    expect(boot).to_be_ok()
    boot_payload = boot.json()
    entrypoint = str(boot_payload.get("entrypoint") or "run_tool")
    source_code = str(boot_payload.get("source_code") or "")

    draft_head_id = boot_payload.get("draft_head_id")
    if draft_head_id:
        lock_payload = {"draft_head_id": draft_head_id, "force": False}
        lock = context.request.post(
            f"{base_url}/api/v1/editor/tools/{tool_id}/draft-lock",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token,
            },
            data=json.dumps(lock_payload),
        )
        if lock.status == 403:
            lock_payload["force"] = True
            lock = context.request.post(
                f"{base_url}/api/v1/editor/tools/{tool_id}/draft-lock",
                headers={
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrf_token,
                },
                data=json.dumps(lock_payload),
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
                "change_summary": "playwright e2e: sandbox file refs + reuse",
                "derived_from_version_id": boot_payload.get("create_draft_from_version_id")
                or boot_payload.get("parent_version_id"),
            }
        ),
    )
    expect(draft).to_be_ok()
    redirect_url = draft.json()["redirect_url"]

    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    editor = page.locator(".cm-editor").first
    expect(editor).to_be_visible(timeout=30_000)
    page.screenshot(path=str(artifacts_dir / "editor-ready.png"), full_page=True)

    return tool_id


def _open_test_mode(page: object) -> object:
    test_mode_button = page.get_by_role("button", name=re.compile(r"^Testkör$", re.IGNORECASE))
    expect(test_mode_button.first).to_be_visible(timeout=30_000)
    test_mode_button.first.click()

    inputs_summary_locator = page.locator(
        "summary", has_text=re.compile(r"Indata\s*\(JSON\)", re.IGNORECASE)
    )
    expect(inputs_summary_locator).to_have_count(1, timeout=30_000)
    inputs_summary = inputs_summary_locator.first
    sandbox_root = inputs_summary.locator("xpath=ancestor::div[contains(@class,'space-y-4')][1]")

    expect(
        sandbox_root.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).first
    ).to_be_visible(timeout=30_000)

    return sandbox_root


def _assert_manifest_path(page: object, *, filename: str) -> None:
    title = page.get_by_text("Indatafiler").first
    expect(title).to_be_visible(timeout=60_000)
    table = title.locator("xpath=..").locator("table")
    expect(table).to_be_visible()
    expect(table.get_by_text(re.compile(rf"/work/input/{re.escape(filename)}"))).to_be_visible(
        timeout=60_000
    )


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/sandbox-file-refs-reuse-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample-inputs.txt"
    sample_file.write_text("File refs sandbox validation.\n", encoding="utf-8")

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
        page.on("response", _log_unauthorized)

        _login(page, base_url=base_url, email=email, password=password)
        _ensure_draft_for_tool(
            context,
            page,
            base_url=base_url,
            tool_slug="demo-inputs-file",
            artifacts_dir=artifacts_dir,
        )

        sandbox = _open_test_mode(page)
        page.screenshot(path=str(artifacts_dir / "test-mode.png"), full_page=True)
        file_input = sandbox.locator("input[type='file']").first
        expect(file_input).to_be_attached()
        file_input.set_input_files(str(sample_file))

        run_endpoint = re.compile(r"/api/v1/editor/tool-versions/.+/run-sandbox")
        file_refs_endpoint = re.compile(r"/api/v1/editor/tool-versions/.+/file-refs")
        with page.expect_response(file_refs_endpoint) as file_refs_response:
            with page.expect_response(run_endpoint) as run_response:
                sandbox.get_by_role(
                    "button", name=re.compile(r"^Testkör kod", re.IGNORECASE)
                ).first.click()
        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        _assert_manifest_path(page, filename=sample_file.name)
        response = run_response.value
        if response.status >= 400:
            raise RuntimeError(f"Sandbox run failed: {response.status} {response.url}")
        run_payload = response.json()
        snapshot_id = run_payload.get("snapshot_id")
        if not snapshot_id:
            raise RuntimeError("Missing snapshot_id on sandbox run result.")
        file_refs_response = file_refs_response.value
        if file_refs_response.status >= 400:
            raise RuntimeError(
                f"File refs fetch failed: {file_refs_response.status} {file_refs_response.url}"
            )
        file_refs_payload = file_refs_response.json()
        file_refs = file_refs_payload.get("files", [])
        if not any(item.get("name") == sample_file.name for item in file_refs):
            raise RuntimeError(f"File refs response missing expected file: {sample_file.name}")
        page.screenshot(path=str(artifacts_dir / "run-with-upload.png"), full_page=True)

        file_input.set_input_files([])
        expect(sandbox.get_by_text(re.compile(r"Inga filer valda", re.IGNORECASE))).to_be_visible()

        sandbox.get_by_role(
            "button", name=re.compile(r"^Välj sparade$", re.IGNORECASE)
        ).first.click()
        ref_label = sandbox.get_by_text(sample_file.name).locator("xpath=ancestor::label[1]")
        expect(ref_label).to_be_visible(timeout=30_000)
        ref_label.locator("input[type='checkbox']").check()

        sandbox.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).first.click()
        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        _assert_manifest_path(page, filename=sample_file.name)
        page.screenshot(path=str(artifacts_dir / "run-with-reuse.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
