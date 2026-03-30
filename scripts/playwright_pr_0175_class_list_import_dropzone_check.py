"""Focused Playwright proof for PR-0175 class-list import drop zone UX.

This browser check validates the shared Klassrumskartan create/edit roster
modal after the drag-and-drop affordance was added. It proves the teacher can
drop a supported file into the new zone, see the updated user-facing guidance,
and continue through the normal preview-first roster flow.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_classroom_planner import login_to_app, wait_for_app_heading
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0175-class-list-import-dropzone-check")
IMPORT_FILE = Path("data/class_list_example_inputs/sa24d_klasslista_komma.txt")
DROPZONE_COPY = "Dra och släpp filen här, eller klicka på knappen för att välja fil."
SUMMARY_COPY = (
    "Klassens namn och elever är ifyllda nedan. Kontrollera att allt stämmer och ändra vid behov."
)


def _open_create_roster_modal(page: Page) -> None:
    """Open the create-roster modal from the overview surface."""

    page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()


def _dispatch_file_drop(page: Page, *, file_path: Path) -> None:
    """Simulate dropping a teacher file into the roster import drop zone."""

    dropzone = page.locator('[data-test="roster-modal-import-dropzone"]')
    expect(dropzone).to_be_visible()
    expect(dropzone).to_contain_text(DROPZONE_COPY)

    page.evaluate(
        """({ fileText, fileName, fileType }) => {
            const dropzone = document.querySelector('[data-test="roster-modal-import-dropzone"]');
            if (!(dropzone instanceof HTMLElement)) {
                throw new Error("Missing roster import drop zone.");
            }
            const dataTransfer = new DataTransfer();
            const file = new File([fileText], fileName, { type: fileType });
            dataTransfer.items.add(file);
            for (const eventType of ["dragenter", "dragover", "drop"]) {
                dropzone.dispatchEvent(
                    new DragEvent(eventType, {
                        bubbles: true,
                        cancelable: true,
                        dataTransfer,
                    }),
                );
            }
        }""",
        {
            "fileText": file_path.read_text(encoding="utf-8"),
            "fileName": file_path.name,
            "fileType": "text/plain",
        },
    )


def _assert_import_prefill(page: Page, *, file_name: str) -> None:
    """Verify the imported preview has been copied into the editable modal fields."""

    import_summary = page.locator('[data-test="roster-import-summary"]')
    expect(import_summary).to_be_visible(timeout=60000)
    expect(import_summary).to_contain_text(file_name)
    expect(import_summary).to_contain_text(re.compile(r"31\s+elever", re.IGNORECASE))
    expect(import_summary).to_contain_text(SUMMARY_COPY)
    expect(page.get_by_label("Klassens namn")).to_have_value("SA24D")
    expect(page.get_by_label("Elever")).to_have_value(re.compile(r"Kerstin Aitman"))


def _save_imported_roster(page: Page, *, roster_name: str) -> None:
    """Persist the imported roster with a deterministic unique name."""

    page.get_by_label("Klassens namn").fill(roster_name)
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_have_count(0)


def _assert_workspace_reconciled(page: Page, *, roster_name: str) -> None:
    """Ensure the saved roster is visible in the class overview after modal close."""

    expect(
        page.get_by_role("heading", name=re.compile(re.escape(roster_name))).first
    ).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="overview-roster-preview"]')).to_contain_text("Kerstin Aitman")


def _assert_edit_modal_dropzone(page: Page) -> None:
    """Open edit mode and verify the same drop zone is available there too."""

    page.locator('[data-test="overview-edit-roster"]').click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_be_visible()
    dropzone = page.locator('[data-test="roster-modal-import-dropzone"]')
    expect(dropzone).to_be_visible()
    expect(dropzone).to_contain_text(DROPZONE_COPY)
    page.get_by_role("button", name=re.compile(r"Avbryt", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_have_count(0)


def main() -> None:
    """Run the focused PR-0175 live proof against the local SPA."""

    if not IMPORT_FILE.is_file():
        raise FileNotFoundError(f"Missing example import file: {IMPORT_FILE}")

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    roster_name = f"SA24D PW0175 {int(time.time())}"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        page.goto(f"{base_url}/apps/classroom.group-seating-studio", wait_until="domcontentloaded")
        wait_for_app_heading(page)

        _open_create_roster_modal(page)
        _dispatch_file_drop(page, file_path=IMPORT_FILE)
        _assert_import_prefill(page, file_name=IMPORT_FILE.name)
        page.screenshot(path=str(ARTIFACTS_DIR / "create-modal-dropzone.png"), full_page=True)
        _save_imported_roster(page, roster_name=roster_name)
        _assert_workspace_reconciled(page, roster_name=roster_name)
        _assert_edit_modal_dropzone(page)
        page.screenshot(
            path=str(ARTIFACTS_DIR / "overview-after-dropzone-save.png"), full_page=True
        )

        context.close()
        browser.close()

    print(f"playwright-pr-0175: ok ({IMPORT_FILE}) -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
