"""Focused Playwright proof for the PR-0120 seating export affordance.

This script validates the live teacher-facing seating export flow through the
real planner UI. It checks the compact export subsection, the default
`Exportera` happy path, the alternate `Affisch (A4)` option, and the resulting
browser downloads without introducing a separate export panel.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Download, Page, expect, sync_playwright

from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0120-seating-export-check")


def _slugify(value: str) -> str:
    """Mirror the conservative output slug contract used by the poster renderer."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"


def _open_seating_workspace(page: Page, *, template_name: str) -> None:
    """Open seating and choose the target classroom in the setup row."""

    focus_workspace_mode(page, label="Sittplatser")
    setup_surface = page.locator('[data-test="seating-workspace-setup"]')
    expect(setup_surface).to_be_visible()
    template_select = setup_surface.get_by_role("combobox")
    option_rows = template_select.evaluate(
        """element => Array.from(element.options).map(option => ({
            value: option.value,
            label: option.label,
        }))"""
    )
    matching_option = next(
        option for option in option_rows if option["value"] and template_name in option["label"]
    )
    template_select.select_option(value=matching_option["value"])
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()
    expect(page.locator('[data-test="seating-export-group"]')).to_be_visible()


def _assign_first_student_to_first_seat(page: Page) -> None:
    """Place one student in the first visible seat before export."""

    seat_drop_target = (
        page.locator('[data-test="room-seat-token"]')
        .filter(has_text=re.compile(r"seat-1", re.IGNORECASE))
        .locator("xpath=ancestor::div[contains(@class, 'absolute')][1]")
    )
    data_transfer = page.evaluate_handle("new DataTransfer()")
    page.get_by_role("button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)).dispatch_event(
        "dragstart",
        {"dataTransfer": data_transfer},
    )
    seat_drop_target.dispatch_event("dragover", {"dataTransfer": data_transfer})
    seat_drop_target.dispatch_event("drop", {"dataTransfer": data_transfer})
    expect(page.locator('[data-test="room-seat-token"]').first).to_contain_text(
        re.compile(r"Ada Lovelace", re.IGNORECASE)
    )


def _save_download(download: Download, *, target_name: str) -> Path:
    """Persist one browser download into the PR artifact directory."""

    target_path = ARTIFACTS_DIR / target_name
    download.save_as(target_path)
    assert target_path.exists()
    return target_path


def _assert_suggested_filename(
    *,
    suggested_name: str,
    roster_name: str,
    paper_size: str,
) -> None:
    """Assert the browser download keeps the teacher-facing export filename semantics."""

    assert suggested_name == f"{_slugify(roster_name)}-{paper_size}.pdf"


def _export_default_a3(page: Page, *, roster_name: str) -> Path:
    """Run the default `Exportera` path and save the downloaded PDF."""

    export_button = page.locator('[data-test="seating-export-default"]')
    expect(export_button).to_have_text(re.compile(r"Exportera", re.IGNORECASE))
    with page.expect_download(timeout=120000) as download_info:
        export_button.click()
    download = download_info.value
    suggested_name = download.suggested_filename
    _assert_suggested_filename(
        suggested_name=suggested_name,
        roster_name=roster_name,
        paper_size="a3_landscape",
    )
    expect(page.locator('[data-test="seating-export-download-latest"]')).to_be_visible(
        timeout=120000
    )
    expect(page.locator('[data-test="seating-export-status"]')).to_contain_text(
        re.compile(r"PDF hämtad och sparad i Mina filer", re.IGNORECASE),
        timeout=120000,
    )
    return _save_download(download, target_name="seating-export-a3.pdf")


def _export_alternate_a4(page: Page, *, roster_name: str) -> Path:
    """Run the alternate `Affisch (A4)` export path and save the download."""

    page.locator('[data-test="seating-export-menu-trigger"]').click()
    expect(page.locator('[data-test="seating-export-option-a4"]')).to_be_visible()
    with page.expect_download(timeout=120000) as download_info:
        page.locator('[data-test="seating-export-option-a4"]').click()
    download = download_info.value
    suggested_name = download.suggested_filename
    _assert_suggested_filename(
        suggested_name=suggested_name,
        roster_name=roster_name,
        paper_size="a4_landscape",
    )
    expect(page.locator('[data-test="seating-export-download-latest"]')).to_be_visible(
        timeout=120000
    )
    return _save_download(download, target_name="seating-export-a4.pdf")


def main() -> None:
    """Run the focused PR-0120 seating export browser proof."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0120 Klass {run_suffix}"
    template_name = f"PW PR0120 Sal {run_suffix}"

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            accept_downloads=True,
        )
        page = context.new_page()

        login_to_app(page, base_url=base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        open_class_workspace(page, roster_name=roster_name)
        _open_seating_workspace(page, template_name=template_name)
        _assign_first_student_to_first_seat(page)

        a3_download = _export_default_a3(page, roster_name=roster_name)
        a4_download = _export_alternate_a4(page, roster_name=roster_name)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "seating-export-ui.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")
    print(f"A3 download: {a3_download}")
    print(f"A4 download: {a4_download}")


if __name__ == "__main__":  # pragma: no cover
    main()
