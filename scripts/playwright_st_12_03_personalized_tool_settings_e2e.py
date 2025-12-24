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


def _login(page: object, *, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()

    dialog.get_by_label("E-post").fill(email)
    dialog.get_by_label("Lösenord").fill(password)
    dialog.get_by_role("button", name=re.compile(r"Logga in", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def _select_tool_id(context: object, *, base_url: str, slug: str) -> str:
    tools_response = context.request.get(f"{base_url}/api/v1/admin/tools")
    expect(tools_response).to_be_ok()
    tools_payload = tools_response.json()
    tools = tools_payload.get("tools", [])
    assert tools, "Expected at least one tool to exist."

    for tool in tools:
        if tool.get("slug") == slug and tool.get("id"):
            return tool["id"]

    raise RuntimeError(f"Tool not found: {slug}")


def _get_editor_boot(context: object, *, base_url: str, tool_id: str) -> dict:
    response = context.request.get(f"{base_url}/api/v1/editor/tools/{tool_id}")
    expect(response).to_be_ok()
    payload = response.json()
    assert isinstance(payload, dict), "Expected editor boot payload to be a dict."
    return payload


def _set_codemirror_value(page: object, source_code: str) -> None:
    content = page.locator(".cm-editor .cm-content").first
    expect(content).to_be_visible()
    content.click()
    content.fill(source_code)


def _save_source(page: object) -> None:
    save_button = page.get_by_role("button", name=re.compile(r"^Spara$", re.IGNORECASE)).first
    expect(save_button).to_be_visible()
    with page.expect_response(
        re.compile(r"/api/v1/editor/(tool-versions/.+/save|tools/.+/draft)$")
    ) as save_response_info:
        save_button.click()

    response = save_response_info.value
    if response.status >= 400:
        raise RuntimeError(f"Save request failed: {response.status} {response.url}")

    page.wait_for_url("**/admin/**", wait_until="domcontentloaded")


def _submit_for_review(page: object) -> None:
    request_button = page.get_by_role(
        "button", name=re.compile(r"Begär publicering", re.IGNORECASE)
    ).first
    expect(request_button).to_be_visible()
    request_button.click()

    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_placeholder("Skriv en kort notis…").fill("ST-12-03 e2e: settings")
    dialog.get_by_role("button", name=re.compile(r"Begär publicering", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()


def _publish(page: object) -> None:
    publish_button = page.get_by_role("button", name=re.compile(r"^Publicera$", re.IGNORECASE)).first
    expect(publish_button).to_be_visible(timeout=20_000)
    publish_button.click()

    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_placeholder("T.ex. uppdaterade regler…").fill("ST-12-03 e2e publish")
    dialog.get_by_role("button", name=re.compile(r"^Publicera$", re.IGNORECASE)).click()
    expect(dialog).not_to_be_visible()


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-12-03-personalized-tool-settings-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hej!\nST-12-03 personalized settings e2e.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password)

        tool_slug = "demo-next-actions"
        tool_id = _select_tool_id(context, base_url=base_url, slug=tool_slug)
        boot_payload = _get_editor_boot(context, base_url=base_url, tool_id=tool_id)
        entrypoint = str(boot_payload.get("entrypoint") or "run_tool").strip() or "run_tool"

        # Edit + publish a version with a settings schema
        page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Källkod", re.IGNORECASE))).to_be_visible()

        schema_textarea = page.get_by_label("Schema (JSON)")
        expect(schema_textarea).to_be_visible()
        schema_textarea.fill('[{"name":"theme_color","label":"Färgtema","kind":"string"}]')

        tool_code = f"""from __future__ import annotations

import json
import os
from pathlib import Path


def {entrypoint}(input_path: str, output_dir: str) -> dict:
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH", "/work/memory.json")
    try:
        memory = json.loads(Path(memory_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        memory = {{}}

    settings = memory.get("settings", {{}}) if isinstance(memory, dict) else {{}}
    theme_color = settings.get("theme_color", "")

    return {{
        "outputs": [
            {{"kind": "notice", "level": "info", "message": f"theme_color={{theme_color}}"}},
            {{"kind": "json", "title": "settings", "value": settings}},
        ],
        "next_actions": [],
        "state": None,
    }}
"""

        _set_codemirror_value(page, tool_code)
        _save_source(page)

        _submit_for_review(page)
        page.screenshot(path=str(artifacts_dir / "in-review.png"), full_page=True)

        _publish(page)
        page.screenshot(path=str(artifacts_dir / "published.png"), full_page=True)

        # Verify runtime settings panel + persistence + runner injection
        page.goto(f"{base_url}/tools/{tool_slug}/run", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=re.compile(r"Demo: Interaktiv", re.IGNORECASE))).to_be_visible()

        settings_toggle = page.get_by_role(
            "button", name=re.compile(r"Inställningar", re.IGNORECASE)
        ).first
        expect(settings_toggle).to_be_visible(timeout=20_000)
        settings_toggle.click()

        theme_field = page.get_by_label("Färgtema").first
        expect(theme_field).to_be_visible()
        theme_field.fill("#ff00ff")

        save_settings = page.get_by_role("button", name=re.compile(r"^Spara$", re.IGNORECASE)).first
        save_settings.click()
        expect(page.get_by_text("Inställningar sparade.")).to_be_visible(timeout=20_000)
        page.screenshot(path=str(artifacts_dir / "settings-saved.png"), full_page=True)

        page.locator("input[type='file']").set_input_files(str(sample_file))
        page.get_by_role("button", name=re.compile(r"^Kör", re.IGNORECASE)).click()

        expect(page.get_by_text("theme_color=#ff00ff")).to_be_visible(timeout=60_000)
        page.screenshot(path=str(artifacts_dir / "run-with-settings.png"), full_page=True)

        page.reload(wait_until="domcontentloaded")
        settings_toggle = page.get_by_role(
            "button", name=re.compile(r"Inställningar", re.IGNORECASE)
        ).first
        settings_toggle.click()
        expect(page.get_by_label("Färgtema").first).to_have_value("#ff00ff")
        page.screenshot(path=str(artifacts_dir / "settings-persisted.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
