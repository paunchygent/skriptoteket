"""Focused Playwright proof for PR-0137 class-list import remediation.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This browser check validates the live Klassrumskartan import flow against the
shipped class-list example inputs. Each file must prefill the class-list modal,
let the teacher save the imported roster without overlay/backdrop breakage, and
reconcile the saved roster straight into the active class workspace.
"""

from __future__ import annotations

import re
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import login_to_app, wait_for_app_heading
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0137-class-list-import-check")
EXAMPLE_IMPORT_FILES = (
    Path("data/class_list_example_inputs/sa24d_klasslista.excel.xls"),
    Path("data/class_list_example_inputs/sa24d_klasslista.pdf"),
    Path("data/class_list_example_inputs/sa24d_klasslista_komma.txt"),
    Path("data/class_list_example_inputs/sa24d_klasslista_tab.txt"),
)


def _open_create_roster_modal(page: Page) -> None:
    """Open the roster-create modal from the overview surface."""

    page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    expect(page.get_by_text(re.compile(r"Skola24", re.IGNORECASE))).to_be_visible()


def _import_file_inside_modal(page: Page, *, file_path: Path) -> None:
    """Upload one shipped example file through the modal-local import control."""

    file_input = page.locator('input[type="file"]').last
    import_summary = page.locator('[data-test="roster-import-summary"]')
    expect(file_input).to_have_attribute("accept", ".xlsx,.xls,.csv,.tsv,.txt,.pdf")
    file_input.set_input_files(str(file_path.resolve()))
    import_timeout_ms = 120000 if file_path.suffix.lower() == ".pdf" else 60000
    expect(import_summary).to_be_visible(timeout=import_timeout_ms)
    expect(import_summary).to_contain_text(re.compile(r"31\s+elever", re.IGNORECASE))
    expect(page.get_by_text(file_path.name, exact=True)).to_be_visible()


def _assert_import_prefill(page: Page) -> None:
    """Verify the imported preview has been copied into the editable modal fields."""

    class_name_input = page.get_by_label("Klassens namn")
    student_textarea = page.get_by_label("Elever")
    expect(class_name_input).to_have_value("SA24D")
    expect(student_textarea).to_have_value(re.compile(r"Kerstin Aitman"))
    expect(student_textarea).to_have_value(re.compile(r"Edith Winlund Strandler"))


def _save_imported_roster(page: Page, *, roster_name: str) -> None:
    """Persist the imported roster with a unique saved name for deterministic lookup."""

    class_name_input = page.get_by_label("Klassens namn")
    class_name_input.fill(roster_name)
    page.get_by_role(
        "button", name=re.compile(r"Skapa klasslista|Spara ändringar", re.IGNORECASE)
    ).click()
    expect(
        page.get_by_role(
            "heading", name=re.compile(r"Ny klasslista|Redigera klasslista", re.IGNORECASE)
        )
    ).to_have_count(0)


def _assert_workspace_reconciled(page: Page, *, roster_name: str) -> None:
    """Ensure save closes preview and opens the imported roster in the overview shell."""

    roster_heading = page.get_by_role("heading", name=re.compile(re.escape(roster_name)))
    expect(roster_heading).to_be_visible(timeout=60000)
    expect(page.get_by_text("Klassarbetsyta", exact=True)).to_be_visible()
    expect(page.locator('[data-test="overview-roster-select"]')).to_have_value(re.compile(r".+"))
    expect(page.locator('[data-test="overview-roster-preview"]')).to_contain_text("Kerstin Aitman")
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_have_count(0)


def _assert_edit_modal_import_entrypoint(page: Page) -> None:
    """Verify edit mode also exposes the import affordance inside the roster workflow."""

    page.get_by_role("button", name="Redigera klass", exact=True).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_be_visible()
    expect(page.locator('[data-test="roster-modal-import-trigger"]')).to_be_visible()
    expect(page.get_by_text(re.compile(r"Skola24", re.IGNORECASE))).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Avbryt", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_have_count(0)


def _build_argument_parser() -> ArgumentParser:
    """Create the CLI parser for selecting which shipped proof file to validate."""

    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file-path",
        type=Path,
        action="append",
        default=[],
        help="Optional path(s) to class-list example file(s) to upload during the live proof.",
    )
    return parser


def main() -> None:
    """Run the focused PR-0137 import flow proof against the local SPA."""

    args, remaining_args = _build_argument_parser().parse_known_args()
    sys.argv = [sys.argv[0], *remaining_args]
    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_suffix = str(int(time.time()))
    import_files = tuple(args.file_path) if args.file_path else EXAMPLE_IMPORT_FILES
    for import_file in import_files:
        if not import_file.is_file():
            raise FileNotFoundError(f"Missing example import file: {import_file}")

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        page.goto(f"{base_url}/apps/classroom.group-seating-studio", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        for index, import_file in enumerate(import_files):
            file_label = import_file.stem.replace(".", "-")
            roster_name = f"SA24D PW0137 {file_label} {run_suffix}"
            _open_create_roster_modal(page)
            _import_file_inside_modal(page, file_path=import_file)
            _assert_import_prefill(page)
            _save_imported_roster(page, roster_name=roster_name)
            _assert_workspace_reconciled(page, roster_name=roster_name)
            if index == 0:
                _assert_edit_modal_import_entrypoint(page)
            page.screenshot(
                path=str(ARTIFACTS_DIR / f"class-list-import-check-{file_label}.png"),
                full_page=True,
            )
        context.close()
        browser.close()

    print(
        "playwright-pr-0137: ok "
        f"({', '.join(str(import_file) for import_file in import_files)}) -> {ARTIFACTS_DIR}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
