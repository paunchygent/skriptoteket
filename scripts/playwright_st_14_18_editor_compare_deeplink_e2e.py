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
            executable_path = _find_chromium_headless_shell()
            if executable_path:
                print(
                    "Headless Chromium failed with macOS permission error; retrying with headless shell."
                )
                return playwright.chromium.launch(headless=True, executable_path=executable_path)
            raise

        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _login(page: object, *, base_url: str, email: str, password: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
    expect(dialog).to_be_visible(timeout=30_000)
    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()

    try:
        expect(
            page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
    except AssertionError:
        page.screenshot(path=str(artifacts_dir / "login-failure.png"), full_page=True)
        raise


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
    if tool.status == 404:
        raise RuntimeError(
            f"Tool slug '{tool_slug}' missing.\n"
            "Seed a tool via the script bank, then retry (see docs/runbooks/runbook-script-bank-seeding.md)."
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
                "change_summary": "playwright e2e: st-14-18 compare deeplink smoke",
                "derived_from_version_id": boot_payload.get("create_draft_from_version_id")
                or boot_payload.get("parent_version_id"),
            }
        ),
    )
    expect(draft).to_be_ok()
    redirect_url = draft.json()["redirect_url"]
    version_id = redirect_url.split("/admin/tool-versions/")[-1].split("?")[0]

    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"Källkod", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )
    return tool_id, version_id


def _ensure_can_edit(page: object) -> None:
    takeover_button = page.get_by_role("button", name=re.compile(r"Ta över lås", re.IGNORECASE))
    if takeover_button.count() > 0 and takeover_button.first.is_visible():
        takeover_button.first.click()
        expect(
            page.get_by_text(re.compile(r"Du har redigeringslåset", re.IGNORECASE))
        ).to_be_visible(timeout=20_000)


def _focus_codemirror(page: object) -> object:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible(timeout=30_000)
    content.click()
    return content


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")

    artifacts_dir = Path(".artifacts/st-14-18-editor-compare-deeplink-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        tool_slug = "demo-inputs-file"

        _login(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
            artifacts_dir=artifacts_dir,
        )

        _, base_version_id = _ensure_draft_for_tool(
            context, page, base_url=base_url, tool_slug=tool_slug
        )
        _ensure_can_edit(page)
        page.screenshot(path=str(artifacts_dir / "editor-loaded.png"), full_page=True)

        base_boot_request_count = 0
        base_boot_re = re.compile(
            rf"/api/v1/editor/tool-versions/{re.escape(base_version_id)}(?:\\?|$)"
        )

        def on_request(request: object) -> None:
            nonlocal base_boot_request_count
            if base_boot_re.search(request.url):
                base_boot_request_count += 1

        page.on("request", on_request)

        marker = "# ST_14_18_E2E_MARKER"
        _focus_codemirror(page)
        page.keyboard.type(f"\n{marker}\n")
        page.wait_for_timeout(1800)  # Debounced IndexedDB head write + slack.

        # Open compare via the explicit CTA (should set compare=... without switching base version).
        open_compare = page.get_by_role(
            "button", name=re.compile(r"Öppna jämförelse", re.IGNORECASE)
        )
        expect(open_compare).to_be_visible(timeout=30_000)
        open_compare.click()

        expect(
            page.get_by_role("heading", name=re.compile(r"Jämför versioner", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
        if "compare=" not in page.url:
            page.screenshot(path=str(artifacts_dir / "missing-compare-param.png"), full_page=True)
            raise RuntimeError(
                f"Expected compare= query param after opening compare, got: {page.url}"
            )

        # Query-only changes should not trigger a base boot reload.
        if base_boot_request_count > 0:
            page.screenshot(
                path=str(artifacts_dir / "unexpected-base-boot-reload.png"), full_page=True
            )
            raise RuntimeError(
                f"Expected no additional base boot requests when opening compare, got: {base_boot_request_count}"
            )

        # The working copy option should become available once a head exists.
        working_option = page.locator("select option[value='working']")
        expect(working_option).to_have_count(1, timeout=30_000)
        if working_option.first.get_attribute("disabled") is not None:
            page.screenshot(path=str(artifacts_dir / "working-option-disabled.png"), full_page=True)
            raise RuntimeError(
                "Expected working compare option to be enabled, but it was disabled."
            )

        # Switching virtual files should update field=... without reloading the base editor.
        page.get_by_role("button", name="input_schema.json", exact=True).click()
        page.wait_for_timeout(250)
        if "field=input_schema.json" not in page.url:
            page.screenshot(path=str(artifacts_dir / "missing-field-param.png"), full_page=True)
            raise RuntimeError(f"Expected field= query param after switching file, got: {page.url}")

        if base_boot_request_count > 0:
            page.screenshot(
                path=str(artifacts_dir / "unexpected-base-boot-reload-field.png"), full_page=True
            )
            raise RuntimeError(
                f"Expected no base boot requests when switching field, got: {base_boot_request_count}"
            )

        page.screenshot(path=str(artifacts_dir / "compare-field-set.png"), full_page=True)

        page.get_by_role("button", name=re.compile(r"Stäng jämförelse", re.IGNORECASE)).click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Källkod", re.IGNORECASE))
        ).to_be_visible(timeout=30_000)
        expect(page.locator(".cm-editor .cm-content").first).to_contain_text(marker, timeout=30_000)
        page.screenshot(path=str(artifacts_dir / "editor-still-dirty.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
