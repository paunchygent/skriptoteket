from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _get_config_value(*, key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


def main() -> None:
    dotenv = _read_dotenv(Path(".env"))

    base_url = _get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000"
    email = _get_config_value(key="BOOTSTRAP_SUPERUSER_EMAIL", dotenv=dotenv)
    password = _get_config_value(key="BOOTSTRAP_SUPERUSER_PASSWORD", dotenv=dotenv)

    if not email or not password:
        raise SystemExit(
            "Missing BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD. "
            "Set them in .env (gitignored) or export them in your shell."
        )

    artifacts_dir = Path(".artifacts/ui-editor-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    marker = uuid.uuid4().hex[:8]
    new_source_code = (
        "def run_tool(input_path: str, output_dir: str) -> str:\n"
        '    return "<p>ok</p>"\n'
        f"# playwright-marker:{marker}\n"
    )

    with sync_playwright() as playwright:
        browser = playwright.webkit.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Login (bootstrap account from .env)
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        page.get_by_label("Lösenord").fill(password)
        page.get_by_role("button", name="Logga in").click()
        expect(page.get_by_text("Inloggad som")).to_be_visible()

        # Navigate to first tool editor page
        page.goto(f"{base_url}/admin/tools", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Testyta")).to_be_visible()

        edit_link = page.get_by_role("link", name="Redigera").first
        if edit_link.count() == 0:
            raise RuntimeError("No tools found in /admin/tools; cannot smoke-test the editor page.")

        edit_link.click()
        page.wait_for_load_state("domcontentloaded")

        # Ensure SPA island mounts (CodeMirror 6)
        expect(page.locator("#spa-editor-main-target .cm-editor")).to_be_visible()

        # Replace editor contents and save (create draft OR save snapshot)
        page.locator("#spa-editor-main-target .cm-content").click()
        page.keyboard.press("Meta+A")
        page.keyboard.type(new_source_code)

        save_button = page.locator("#spa-editor-sidebar-target button").first
        expect(save_button).to_be_visible()
        save_button.click()

        page.wait_for_url("**/admin/tool-versions/**", wait_until="domcontentloaded")
        expect(page.locator("#toast-container .huleedu-toast")).to_contain_text(
            re.compile(r"(Utkast skapat\.|Sparat\.)")
        )

        # Ensure the new server-rendered payload contains the marker (persisted)
        payload_text = page.locator("#spa-island-editor-payload").text_content() or ""
        assert marker in payload_text, "Saved payload did not include the expected marker."

        # Ensure island mounts after redirect, too.
        expect(page.locator("#spa-editor-main-target .cm-editor")).to_be_visible()
        page.screenshot(path=str(artifacts_dir / "editor.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright editor smoke screenshot written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
