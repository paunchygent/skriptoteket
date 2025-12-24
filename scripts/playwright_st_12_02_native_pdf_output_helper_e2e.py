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


def _login(
    page: object,
    *,
    base_url: str,
    email: str,
    password: str,
    artifacts_dir: Path | None = None,
) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("main").get_by_role(
        "button", name=re.compile(r"Logga in", re.IGNORECASE)
    ).click()
    try:
        expect(
            page.get_by_role("heading", name=re.compile(r"Välkommen", re.IGNORECASE))
        ).to_be_visible(timeout=15_000)
    except AssertionError:
        if artifacts_dir:
            page.screenshot(path=str(artifacts_dir / "login-failure.png"), full_page=True)
        raise


def _select_tool_id(context: object, *, base_url: str, preferred_slug: str) -> str:
    tools_response = context.request.get(f"{base_url}/api/v1/admin/tools")
    expect(tools_response).to_be_ok()
    tools_payload = tools_response.json()
    tools = tools_payload.get("tools", [])
    assert tools, "Expected at least one tool to exist for PDF helper E2E."

    for tool in tools:
        if tool.get("slug") == preferred_slug and tool.get("id"):
            return tool["id"]

    first_id = tools[0].get("id")
    assert first_id, "Expected tool id in admin tools payload."
    return first_id


def _get_editor_boot(context: object, *, base_url: str, tool_id: str) -> dict:
    response = context.request.get(f"{base_url}/api/v1/editor/tools/{tool_id}")
    expect(response).to_be_ok()
    payload = response.json()
    assert isinstance(payload, dict), "Expected editor boot payload to be a dict."
    return payload


def _ensure_selected_version(page: object) -> None:
    missing_version = page.get_by_text("Spara ett utkast för att kunna testa.")
    if missing_version.count() > 0 and missing_version.is_visible():
        save_button = page.get_by_role("button", name=re.compile(r"^Spara$", re.IGNORECASE)).first
        expect(save_button).to_be_visible()
        save_button.click()

        page.wait_for_url("**/admin/**", wait_until="domcontentloaded")

    expect(
        page.get_by_role("button", name=re.compile(r"Testkör kod", re.IGNORECASE))
    ).to_be_visible()


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

    expect(page.locator(".cm-editor").first).to_be_visible(timeout=20_000)


def _upload_single_file(page: object, *, file_path: Path) -> None:
    file_input = page.locator("input[type='file']").first
    expect(file_input).to_be_attached()
    file_input.set_input_files(str(file_path))


def _run_sandbox(page: object) -> None:
    run_button = page.get_by_role("button", name=re.compile(r"Testkör kod", re.IGNORECASE)).first
    expect(run_button).to_be_visible()
    run_button.click()


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-12-02-native-pdf-output-helper-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_file = artifacts_dir / "sample.txt"
    sample_file.write_text("Hej!\nPDF helper E2E.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()

        _login(page, base_url=base_url, email=email, password=password, artifacts_dir=artifacts_dir)

        tool_id = _select_tool_id(context, base_url=base_url, preferred_slug="demo-next-actions")
        boot_payload = _get_editor_boot(context, base_url=base_url, tool_id=tool_id)

        entrypoint = str(boot_payload.get("entrypoint") or "run_tool")
        original_source = str(boot_payload.get("source_code") or "")

        page.goto(f"{base_url}/admin/tools/{tool_id}", wait_until="domcontentloaded")
        expect(
            page.get_by_role("heading", name=re.compile(r"Testkör kod", re.IGNORECASE))
        ).to_be_visible()
        _ensure_selected_version(page)

        pdf_success_code = f"""from __future__ import annotations

from pathlib import Path

from pdf_helper import save_as_pdf


def {entrypoint}(input_dir: str, output_dir: str) -> dict:
    html_content = \"\"\"<!DOCTYPE html>
<html>
  <head>
    <meta charset=\\"utf-8\\">
    <title>Rapport</title>
    <style>
      @page {{ size: A4; margin: 18mm; }}
      body {{ font-family: Liberation Sans, DejaVu Sans, sans-serif; }}
      h1 {{ font-size: 20pt; margin: 0 0 8mm 0; }}
      .meta {{ color: #444; font-size: 10pt; margin-bottom: 6mm; }}
      .box {{ border: 1px solid #111; padding: 6mm; }}
    </style>
  </head>
  <body>
    <h1>PDF-demo</h1>
    <div class=\\"meta\\">Native PDF output helper (ST-12-02)</div>
    <div class=\\"box\\">
      <p>Om du ser <strong>rapport.pdf</strong> under <em>Filer</em> fungerar helpern.</p>
    </div>
  </body>
</html>
\"\"\"

    pdf_path = save_as_pdf(html_content, output_dir, "rapport.pdf")

    return {{
        "outputs": [
            {{"kind": "notice", "level": "info", "message": "PDF skapad!"}},
            {{"kind": "markdown", "markdown": f"Ladda ner **{{Path(pdf_path).name}}** under Filer."}},
        ],
        "next_actions": [],
        "state": None,
    }}
"""

        _set_codemirror_value(page, pdf_success_code)
        _save_source(page)

        _upload_single_file(page, file_path=sample_file)
        _run_sandbox(page)

        expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
            timeout=60_000
        )
        page.screenshot(path=str(artifacts_dir / "run-success.png"), full_page=True)

        pdf_link = page.get_by_role("link", name="output/rapport.pdf").first
        expect(pdf_link).to_be_visible(timeout=60_000)

        with page.expect_download() as download_info:
            pdf_link.click()
        download = download_info.value
        downloaded_path = artifacts_dir / "rapport.pdf"
        download.save_as(str(downloaded_path))

        header = downloaded_path.read_bytes()[:5]
        assert header == b"%PDF-", f"Expected PDF header, got {header!r}"

        pdf_failure_code = f"""from __future__ import annotations

from pathlib import Path

from pdf_helper import save_as_pdf


def {entrypoint}(input_dir: str, output_dir: str) -> dict:
    # Force a write failure by creating a directory at the PDF output path.
    output = Path(output_dir)
    (output / "rapport.pdf").mkdir(parents=True, exist_ok=True)

    html_content = \"\"\"<!DOCTYPE html><html><body><h1>Broken PDF</h1></body></html>\"\"\"
    save_as_pdf(html_content, output_dir, "rapport.pdf")

    return {{
        "outputs": [{{"kind": "notice", "level": "info", "message": "Should not reach."}}],
        "next_actions": [],
        "state": None,
    }}
"""

        clear_button = page.get_by_role("button", name=re.compile(r"Rensa", re.IGNORECASE))
        if clear_button.count() > 0 and clear_button.first.is_visible():
            clear_button.first.click()

        _set_codemirror_value(page, pdf_failure_code)
        _save_source(page)

        _upload_single_file(page, file_path=sample_file)
        _run_sandbox(page)

        expect(page.get_by_text("Misslyckades", exact=True)).to_be_visible(timeout=60_000)
        error_summary = (
            page.locator("pre").filter(has_text=re.compile(r"PDF-rendering", re.IGNORECASE)).first
        )
        expect(error_summary).to_be_visible(timeout=60_000)
        error_text = error_summary.text_content() or ""
        assert "Traceback" not in error_text, "Expected safe error summary without traceback."
        page.screenshot(path=str(artifacts_dir / "run-failure.png"), full_page=True)

        if original_source:
            _set_codemirror_value(page, original_source)
            _save_source(page)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
