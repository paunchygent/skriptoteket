"""Playwright E2E: vault save + picker + delete/restore (ST-14-36).

Flow:
1) Production tool run (html-to-pdf-preview): upload HTML, convert to PDF.
2) Save produced PDF artifact to vault via "Spara i valv".
3) Vault UI: search, delete -> trash, restore -> active.
4) Production tool run (demo-inputs-file): pick saved vault file and verify /work/input path.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import (
    Browser,
    Page,
    Playwright,
    Response,
    expect,
    sync_playwright,
)
from playwright.sync_api import (
    Error as PlaywrightError,
)

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


def _launch_chromium(playwright: Playwright) -> Browser:
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


def _log_unauthorized(response: Response) -> None:
    try:
        if response.status == 401:
            print(f"[401] {response.url}")
    except Exception:
        return


def _login(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    target_path: str,
) -> None:
    page.goto(f"{base_url}{target_path}", wait_until="domcontentloaded")

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


def _create_sample_html(*, artifacts_dir: Path) -> tuple[Path, str]:
    html_path = artifacts_dir / "sample.html"
    html_path.write_text(
        """<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8" />
    <title>ST-14-36</title>
    <style>
      body { font-family: sans-serif; }
      h1 { margin: 0 0 12px 0; }
      .note { color: #444; font-size: 12px; }
    </style>
  </head>
  <body>
    <h1>Vault</h1>
    <p class="note">ST-14-36: save artifact to vault and reuse as file-ref input.</p>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return html_path, "sample.pdf"


def _run_html_to_pdf_and_save_to_vault(
    page: Page, *, base_url: str, html_path: Path, expected_pdf: str
) -> None:
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

    artifact_row = pdf_link.first.locator("xpath=ancestor::li[1]")
    save_button = artifact_row.get_by_role(
        "button", name=re.compile(r"Spara i valv", re.IGNORECASE)
    )
    expect(save_button).to_be_visible(timeout=60_000)
    save_button.click()

    expect(page.get_by_text("Sparade filen i valvet.")).to_be_visible(timeout=60_000)


def _delete_restore_in_vault_ui(page: Page, *, base_url: str, filename: str) -> None:
    page.goto(f"{base_url}/vault", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"Valv", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )

    search_input = page.get_by_placeholder(re.compile(r"Sök på filnamn", re.IGNORECASE)).first
    expect(search_input).to_be_visible(timeout=30_000)
    search_input.fill(filename)
    search_input.press("Enter")

    row = page.locator("li", has=page.get_by_text(filename)).first
    expect(row).to_be_visible(timeout=60_000)

    row.get_by_role("button", name=re.compile(r"^Ta bort$", re.IGNORECASE)).click()
    expect(page.get_by_text("Filen flyttades till papperskorgen.")).to_be_visible(timeout=60_000)

    page.get_by_role("button", name=re.compile(r"^Papperskorg$", re.IGNORECASE)).click()

    trash_row = page.locator("li", has=page.get_by_text(filename)).first
    expect(trash_row).to_be_visible(timeout=60_000)
    trash_row.get_by_role("button", name=re.compile(r"^Återställ$", re.IGNORECASE)).click()
    expect(page.get_by_text("Filen återställdes.")).to_be_visible(timeout=60_000)

    page.get_by_role("button", name=re.compile(r"^Aktiva$", re.IGNORECASE)).click()
    active_row = page.locator("li", has=page.get_by_text(filename)).first
    expect(active_row).to_be_visible(timeout=60_000)


def _assert_manifest_path(page: Page, *, filename: str) -> None:
    title = page.get_by_text("Indatafiler").first
    expect(title).to_be_visible(timeout=60_000)
    table = title.locator("xpath=..").locator("table")
    expect(table).to_be_visible()
    expect(table.get_by_text(re.compile(rf"/work/input/{re.escape(filename)}"))).to_be_visible(
        timeout=60_000
    )


def _run_demo_inputs_file_with_vault_ref(page: Page, *, base_url: str, filename: str) -> None:
    page.goto(f"{base_url}/tools/demo-inputs-file/run", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"demo", re.IGNORECASE))).to_be_visible(
        timeout=30_000
    )

    page.get_by_role("button", name=re.compile(r"^Välj sparade$", re.IGNORECASE)).first.click()
    page.get_by_role("button", name=re.compile(r"^Välj i valvet$", re.IGNORECASE)).first.click()

    modal = page.get_by_role("dialog")
    expect(modal).to_be_visible(timeout=30_000)
    search_input = modal.get_by_placeholder(re.compile(r"Sök på filnamn", re.IGNORECASE)).first
    expect(search_input).to_be_visible(timeout=30_000)
    search_input.fill(filename)
    search_input.press("Enter")

    modal_row = modal.locator("li", has=modal.get_by_text(filename)).first
    expect(modal_row).to_be_visible(timeout=60_000)
    modal_row.get_by_role("checkbox").first.check()

    modal.get_by_role("button", name=re.compile(r"^Välj$", re.IGNORECASE)).click()
    expect(modal).not_to_be_visible(timeout=30_000)

    page.get_by_role("button", name=re.compile(r"^Kör$", re.IGNORECASE)).click()
    _assert_manifest_path(page, filename=filename)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/st-14-36-vault-ui-e2e")
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
        page.on("response", _log_unauthorized)

        _login(
            page,
            base_url=base_url,
            email=email,
            password=password,
            target_path="/tools/html-to-pdf-preview/run",
        )

        _run_html_to_pdf_and_save_to_vault(
            page, base_url=base_url, html_path=html_path, expected_pdf=expected_pdf
        )
        page.screenshot(path=str(artifacts_dir / "saved-to-vault.png"), full_page=True)

        _delete_restore_in_vault_ui(page, base_url=base_url, filename=expected_pdf)
        page.screenshot(path=str(artifacts_dir / "vault-managed.png"), full_page=True)

        _run_demo_inputs_file_with_vault_ref(page, base_url=base_url, filename=expected_pdf)
        page.screenshot(path=str(artifacts_dir / "vault-picked.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")
    print("ST-14-36 vault UI E2E passed!")


if __name__ == "__main__":
    main()
