"""Playwright E2E test for ST-12-05 session-scoped file persistence.

Verifies the html-to-pdf-preview demo tool works end-to-end without re-upload:
1) Production tool run: upload HTML, run preview, click "Konvertera till PDF" -> PDF is produced.
2) Editor sandbox: same flow inside SandboxRunner for a draft version.
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
    page.locator("form").get_by_role(
        "button", name=re.compile(r"^Logga in$", re.IGNORECASE)
    ).click()
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def _ensure_draft_for_tool(
    context: object,
    page: object,
    *,
    base_url: str,
    tool_slug: str,
) -> str:
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
                "change_summary": "playwright e2e: ST-12-05",
            }
        ),
    )
    expect(draft).to_be_ok()
    redirect_url = draft.json()["redirect_url"]
    version_id = redirect_url.split("/admin/tool-versions/")[-1].split("?")[0]

    page.goto(f"{base_url}{redirect_url}", wait_until="domcontentloaded")
    expect(
        page.get_by_role("button", name=re.compile(r"Testkör kod", re.IGNORECASE))
    ).to_be_visible(timeout=30_000)

    return version_id


def _create_sample_html(*, artifacts_dir: Path) -> tuple[Path, str]:
    html_path = artifacts_dir / "sample.html"
    html_path.write_text(
        """<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8" />
    <title>ST-12-05</title>
    <style>
      body { font-family: sans-serif; }
      h1 { margin: 0 0 12px 0; }
      .note { color: #444; font-size: 12px; }
    </style>
  </head>
  <body>
    <h1>Session files</h1>
    <p class="note">ST-12-05: html-to-pdf-preview should convert without re-upload.</p>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return html_path, "sample.pdf"


def _run_production_flow(
    page: object, *, base_url: str, html_path: Path, expected_pdf: str
) -> Path:
    page.goto(f"{base_url}/tools/html-to-pdf-preview/run", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"HTML.*PDF", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )

    file_input = page.locator("input[type='file']").first
    expect(file_input).to_be_attached()
    file_input.set_input_files(str(html_path))

    page.get_by_role("button", name=re.compile(r"^Kör$", re.IGNORECASE)).click()
    expect(page.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(timeout=60_000)

    page_size = page.get_by_role("group", name=re.compile(r"Sidstorlek", re.IGNORECASE))
    expect(page_size.first).to_be_visible(timeout=60_000)
    page_size.get_by_label(re.compile(r"^A4$", re.IGNORECASE)).first.check()

    orientation = page.get_by_role("group", name=re.compile(r"Orientering", re.IGNORECASE))
    expect(orientation.first).to_be_visible(timeout=60_000)
    orientation.get_by_label(re.compile(r"Stående", re.IGNORECASE)).first.check()
    page.get_by_role("button", name=re.compile(r"Konvertera till PDF", re.IGNORECASE)).first.click()

    expect(page.get_by_text(re.compile(r"Konverteringsresultat", re.IGNORECASE))).to_be_visible(
        timeout=60_000
    )
    pdf_link = page.get_by_role("link", name=f"output/{expected_pdf}")
    expect(pdf_link.first).to_be_visible(timeout=60_000)

    downloaded_path = html_path.parent / "production.pdf"
    with page.expect_download() as download_info:
        pdf_link.first.click()
    download = download_info.value
    download.save_as(str(downloaded_path))

    header = downloaded_path.read_bytes()[:5]
    assert header == b"%PDF-", f"Expected PDF header, got {header!r}"
    return downloaded_path


def _get_sandbox_section(page: object) -> object:
    return page.get_by_text("Testfiler").locator(
        "xpath=ancestor::div[contains(@class,'space-y-4')][1]"
    )


def _run_editor_sandbox_flow(page: object, *, html_path: Path, expected_pdf: str) -> Path:
    sandbox = _get_sandbox_section(page)

    file_input = page.locator("input[type='file']").first
    expect(file_input).to_be_attached()
    file_input.set_input_files(str(html_path))

    sandbox.get_by_role("button", name=re.compile(r"^Testkör kod", re.IGNORECASE)).first.click()
    expect(sandbox.get_by_text(re.compile(r"Lyckades", re.IGNORECASE))).to_be_visible(
        timeout=60_000
    )

    page_size = sandbox.get_by_role("group", name=re.compile(r"Sidstorlek", re.IGNORECASE))
    expect(page_size.first).to_be_visible(timeout=60_000)
    page_size.get_by_label(re.compile(r"^A4$", re.IGNORECASE)).first.check()

    orientation = sandbox.get_by_role("group", name=re.compile(r"Orientering", re.IGNORECASE))
    expect(orientation.first).to_be_visible(timeout=60_000)
    orientation.get_by_label(re.compile(r"Stående", re.IGNORECASE)).first.check()
    sandbox.get_by_role(
        "button", name=re.compile(r"Konvertera till PDF", re.IGNORECASE)
    ).first.click()

    expect(sandbox.get_by_text(re.compile(r"Konverteringsresultat", re.IGNORECASE))).to_be_visible(
        timeout=60_000
    )
    pdf_link = sandbox.get_by_role("link", name=f"output/{expected_pdf}")
    expect(pdf_link.first).to_be_visible(timeout=60_000)

    downloaded_path = html_path.parent / "sandbox.pdf"
    with page.expect_download() as download_info:
        pdf_link.first.click()
    download = download_info.value
    download.save_as(str(downloaded_path))

    header = downloaded_path.read_bytes()[:5]
    assert header == b"%PDF-", f"Expected PDF header, got {header!r}"
    return downloaded_path


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-12-05-session-file-persistence-e2e")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    html_path, expected_pdf = _create_sample_html(artifacts_dir=artifacts_dir)

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

        _login(page, base_url=base_url, email=email, password=password)

        production_pdf = _run_production_flow(
            page, base_url=base_url, html_path=html_path, expected_pdf=expected_pdf
        )
        print(f"Production OK (downloaded): {production_pdf}")

        _ensure_draft_for_tool(context, page, base_url=base_url, tool_slug="html-to-pdf-preview")
        sandbox_pdf = _run_editor_sandbox_flow(page, html_path=html_path, expected_pdf=expected_pdf)
        print(f"Editor sandbox OK (downloaded): {sandbox_pdf}")

        page.screenshot(path=str(artifacts_dir / "done.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")
    print("ST-12-05 session file persistence E2E passed!")


if __name__ == "__main__":
    main()
