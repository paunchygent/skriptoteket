"""Focused live proof for the seating student-pool drag preview.

This script verifies that dragging a student from the seating workspace's class
list now uses the same circular seat-token language as the live seating canvas
before the student is dropped onto a target seat.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_classroom_planner import (
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config
from scripts.playwright_ui_smoke import _launch_chromium

ARTIFACTS_DIR = Path(".artifacts/seating-drag-preview-check")


def _open_seating_workspace(page, *, template_name: str) -> None:
    """Open seating and select the requested classroom."""

    focus_workspace_mode(page, label="Sittplatser")
    template_select = page.locator('[data-test="seating-template-select"]')
    expect(template_select).to_be_visible()
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


def main() -> None:
    """Verify the seating pool drag preview uses the seat-token language."""

    config = get_config()
    timestamp = int(time.time())
    roster_name = f"Drag Preview Klass {timestamp}"
    template_name = f"Drag Preview Sal {timestamp}"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1100})
        page = context.new_page()

        login_to_app(page, base_url=config.base_url, email=config.email, password=config.password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        open_class_workspace(page, roster_name=roster_name)
        _open_seating_workspace(page, template_name=template_name)

        student_button = page.get_by_role(
            "button", name=re.compile(r"Ada Lovelace", re.IGNORECASE)
        ).first
        data_transfer = page.evaluate_handle("new DataTransfer()")

        student_button.dispatch_event("dragstart", {"dataTransfer": data_transfer})

        preview = page.locator('[data-test="seat-drag-preview"]')
        expect(preview).to_have_count(1)
        preview_details = preview.evaluate(
            """element => ({
                text: element.textContent,
                borderRadius: getComputedStyle(element).borderRadius,
                width: getComputedStyle(element).width,
                height: getComputedStyle(element).height,
            })"""
        )
        assert preview_details["text"] and "Ada Lovelace" in preview_details["text"]
        assert preview_details["borderRadius"] != "0px"
        assert preview_details["width"] == preview_details["height"]

        student_button.dispatch_event("dragend", {"dataTransfer": data_transfer})
        expect(preview).to_have_count(0)

        page.screenshot(
            path=str(ARTIFACTS_DIR / "seating-drag-preview-check.png"),
            full_page=True,
        )
        context.close()
        browser.close()

    print(f"playwright-seating-drag-preview: ok -> {ARTIFACTS_DIR}")


if __name__ == "__main__":  # pragma: no cover
    main()
