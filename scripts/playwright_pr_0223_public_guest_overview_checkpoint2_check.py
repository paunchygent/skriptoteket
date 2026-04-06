"""Focused Playwright proof for PR-0223 public guest checkpoint 3.

This script is a targeted browser proof for a bounded public Klassrumskartan
slice. It validates that the public guest shell can author rosters and room
templates in the browser-owned workspace, continue into Grupper and
Sittplatser, keep draft continuity across overview returns, preserve the final
registration message, and avoid owner-scoped authenticated planner APIs.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, expect, sync_playwright

from scripts._playwright_browser import launch_chromium

ARTIFACTS_DIR = Path(".artifacts/pr-0223-public-guest-checkpoint3")
IMPORT_FILE = Path("data/class_list_example_inputs/sa24d_klasslista_komma.txt")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
FINAL_GUEST_MESSAGE = (
    "Vissa funktioner kräver att du registrerar ett konto. Tryck här för att skapa ett."
)
IMPORT_SUMMARY_COPY = (
    "Klassens namn och elever är ifyllda nedan. Kontrollera att allt stämmer och ändra vid behov."
)
BLOCKED_OWNER_SCOPED_PREFIXES = (
    "/api/v1/apps/classroom.group-seating-studio",
    "/api/v1/catalog",
)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the focused public-route check."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Base URL for the public SPA host (default: http://127.0.0.1:5173).",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=str(ARTIFACTS_DIR),
        help="Artifacts output directory.",
    )
    return parser.parse_args()


def _normalize_visible_text(page: Page) -> str:
    """Return the page body text as one collapsed string."""

    return re.sub(r"\s+", " ", page.locator("body").inner_text()).strip()


def _assert_final_guest_message(page: Page) -> None:
    """Verify the public guest system message uses the final approved copy."""

    message = page.locator('[data-test="public-guest-system-message"]')
    expect(message).to_be_visible()
    expect(message).to_contain_text(FINAL_GUEST_MESSAGE)
    register_link = message.get_by_role("link", name="här", exact=True)
    expect(register_link).to_have_attribute("href", "/register")


def _open_create_roster_modal(page: Page) -> None:
    """Open the create-roster modal from the public overview shell."""

    page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()


def _import_roster_preview(page: Page) -> None:
    """Upload the checkpoint import fixture and wait for the preview summary."""

    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(IMPORT_FILE))
    import_summary = page.locator('[data-test="roster-import-summary"]')
    expect(import_summary).to_be_visible(timeout=60000)
    expect(import_summary).to_contain_text(IMPORT_FILE.name)
    expect(import_summary).to_contain_text(IMPORT_SUMMARY_COPY)
    expect(page.get_by_label("Klassens namn")).to_have_value("SA24D")


def _create_roster(page: Page, *, roster_name: str) -> None:
    """Create one guest roster through the public import-preview flow."""

    _open_create_roster_modal(page)
    _import_roster_preview(page)
    page.get_by_label("Klassens namn").fill(roster_name)
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_have_count(0)
    expect(page.locator('[data-test="overview-roster-preview"]')).to_contain_text("Kerstin Aitman")
    option_labels = page.locator('[data-test="overview-roster-select"]').evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert any(roster_name in label for label in option_labels)


def _edit_roster(page: Page, *, edited_name: str) -> None:
    """Rename the currently selected roster through the public edit modal."""

    page.locator('[data-test="overview-edit-roster"]').click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_label("Klassens namn").fill(edited_name)
    students = page.get_by_label("Elever")
    students.fill(f"{students.input_value()}\nExtra Elev")
    page.get_by_role("button", name=re.compile(r"Spara ändringar", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klasslista", re.IGNORECASE))
    ).to_have_count(0)
    option_labels = page.locator('[data-test="overview-roster-select"]').evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert any(edited_name in label for label in option_labels)
    expect(page.locator('[data-test="overview-roster-preview"]')).to_contain_text("Extra Elev")


def _delete_roster(page: Page) -> None:
    """Delete the selected roster through the overview confirmation dialog."""

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    page.locator('[data-test="overview-delete-roster"]').click()
    heading = page.get_by_role("heading", name="Är du säker?", exact=True)
    expect(heading).to_be_visible()
    expect(page.get_by_text("Klasslistan", exact=False)).to_be_visible()
    page.locator('[data-test="confirm-dialog-confirm"]').click()
    expect(heading).not_to_be_visible(timeout=60000)
    expect(page.locator('[data-test="overview-roster-select"]')).to_have_value("")
    expect(page.locator('[data-test="overview-roster-preview"]')).to_contain_text(
        "Välj en klasslista för att visa en kompakt elevöversikt här."
    )


def _create_template(page: Page, *, template_name: str) -> None:
    """Create one compact room template through the public overview shell."""

    page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)

    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    expect(grid_buttons.nth(0)).to_be_visible()
    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_have_count(0)
    option_labels = page.locator('[data-test="overview-template-select"]').evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert any(template_name in label for label in option_labels)


def _open_workspace_mode(page: Page, *, label: str) -> None:
    """Switch between overview/grouping/seating using the shared top-panel toggle."""

    page.locator(f'[data-test="planner-mode-{label}"]').last.click(force=True)


def _wait_for_guest_workspace_entry(page: Page) -> None:
    """Wait for the guest overview to enable both planner entry points."""

    expect(page.locator('[data-test="planner-mode-grouping"]')).to_be_enabled()
    expect(page.locator('[data-test="planner-mode-seating"]')).to_be_enabled()


def _wait_for_overview_shell(page: Page) -> None:
    """Wait for the overview shell to become the only active mode-switch surface."""

    expect(page.locator('[data-test="overview-roster-preview"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-test="overview-template-select"]')).to_be_visible(timeout=10000)
    page.wait_for_function(
        """
        () => document.querySelectorAll('[data-test="planner-mode-seating"]').length === 1
        """
    )


def _wait_for_grouping_workspace(page: Page) -> None:
    """Wait for the dedicated guest grouping shell to finish replacing overview."""

    expect(page.locator('[data-test="new-grouping-draft"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-test="grouping-board-lane"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-test="grouping-student-pool"]')).to_contain_text("Ej grupperade")
    expect(page.locator('[data-test="planner-mode-rules"]')).to_have_count(0)


def _wait_for_seating_workspace(page: Page) -> None:
    """Wait for the dedicated guest seating shell to finish replacing overview."""

    expect(page.locator('[data-test="seating-workspace-lane"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-test="seating-template-select"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-test="planner-mode-rules"]')).to_have_count(0)


def _assert_grouping_draft_continuity(page: Page, *, artifacts_dir: Path) -> None:
    """Verify the guest grouping draft persists when returning to overview."""

    _open_workspace_mode(page, label="grouping")
    _wait_for_grouping_workspace(page)
    page.screenshot(path=str(artifacts_dir / "guest-grouping-workspace.png"), full_page=True)

    _open_workspace_mode(page, label="overview")
    expect(page.locator('[data-test="overview-roster-preview"]')).to_be_visible()

    _open_workspace_mode(page, label="grouping")
    _wait_for_grouping_workspace(page)


def _assert_seating_entry_and_continuity(
    page: Page,
    *,
    expected_template_name: str,
    artifacts_dir: Path,
) -> None:
    """Verify the guest seating shell opens and keeps the selected classroom."""

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    expect(page.locator('[data-test="overview-classroom-empty"]')).to_have_count(0)

    _open_workspace_mode(page, label="seating")
    _wait_for_seating_workspace(page)
    selected_label = page.locator('[data-test="seating-template-select"]').evaluate(
        "element => element.selectedOptions[0]?.label ?? ''"
    )
    assert expected_template_name in selected_label

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    expect(page.locator('[data-test="overview-template-select"]')).to_have_value(re.compile(r".+"))

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    expect(page.locator('[data-test="overview-template-select"]')).to_have_value(re.compile(r".+"))
    page.screenshot(path=str(artifacts_dir / "guest-seating-workspace.png"), full_page=True)

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    expect(page.locator('[data-test="overview-template-select"]')).to_have_value(re.compile(r".+"))

    _open_workspace_mode(page, label="seating")
    _wait_for_seating_workspace(page)
    selected_label = page.locator('[data-test="seating-template-select"]').evaluate(
        "element => element.selectedOptions[0]?.label ?? ''"
    )
    assert expected_template_name in selected_label


def _edit_template(page: Page, *, edited_name: str) -> None:
    """Rename the selected template through the public room-template modal."""

    page.locator('[data-test="overview-edit-template"]').click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(edited_name)
    page.get_by_role("button", name=re.compile(r"Spara klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Redigera klassrum", re.IGNORECASE))
    ).to_have_count(0)
    option_labels = page.locator('[data-test="overview-template-select"]').evaluate(
        "element => Array.from(element.options).map(option => option.label)"
    )
    assert any(edited_name in label for label in option_labels)


def _select_overview_option_by_label(
    page: Page,
    *,
    selector: str,
    expected_label_fragment: str,
) -> None:
    """Select an overview roster/template option by matching part of its label."""

    value = page.locator(selector).evaluate(
        """
        (element, expectedLabelFragment) => {
          const option = Array.from(element.options).find(
            (candidate) => candidate.label.includes(expectedLabelFragment),
          );
          return option ? option.value : null;
        }
        """,
        expected_label_fragment,
    )
    if not value:
        raise AssertionError(
            f"Could not find overview option containing label fragment: {expected_label_fragment}"
        )
    page.locator(selector).select_option(value)


def _delete_template(page: Page) -> None:
    """Delete the selected room template through the overview confirmation dialog."""

    _open_workspace_mode(page, label="overview")
    _wait_for_overview_shell(page)
    page.locator('[data-test="overview-delete-template"]').click()
    heading = page.get_by_role("heading", name="Är du säker?", exact=True)
    expect(heading).to_be_visible()
    expect(page.get_by_text("Klassrummet", exact=False)).to_be_visible()
    page.locator('[data-test="confirm-dialog-confirm"]').click()
    expect(heading).not_to_be_visible(timeout=60000)
    expect(page.locator('[data-test="overview-template-select"]')).to_have_value("")
    expect(page.locator('[data-test="overview-classroom-empty"]')).to_contain_text(
        "Välj ett klassrum i listan ovan för att visa en kompakt förhandsgranskning här."
    )


def _collect_api_response(api_responses: list[dict[str, object]], response: Response) -> None:
    """Record one API response so the proof can audit the live network surface."""

    url = response.url
    parsed = urlparse(url)
    if not parsed.path.startswith("/api/v1/"):
        return

    api_responses.append(
        {
            "method": response.request.method,
            "path": parsed.path,
            "status": response.status,
        }
    )


def _assert_no_owner_scoped_api_calls(api_responses: list[dict[str, object]]) -> None:
    """Fail if the public guest flow touched owner-scoped authenticated APIs."""

    blocked = [
        entry
        for entry in api_responses
        if any(
            str(entry.get("path")).startswith(prefix) for prefix in BLOCKED_OWNER_SCOPED_PREFIXES
        )
    ]
    if blocked:
        raise AssertionError(f"Observed owner-scoped API calls: {blocked}")

    observed_paths = {str(entry["path"]) for entry in api_responses}
    required_paths = {
        "/api/v1/public/apps/classroom.group-seating-studio",
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
    }
    missing_paths = required_paths - observed_paths
    if missing_paths:
        raise AssertionError(f"Missing expected public API calls: {sorted(missing_paths)}")


def main() -> None:
    """Run the checkpoint-3 public guest browser-owned planner proof."""

    if not IMPORT_FILE.is_file():
        raise FileNotFoundError(f"Missing example import file: {IMPORT_FILE}")

    args = _parse_args()
    base_url = args.base_url.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PW PR0223 Klass {run_suffix}"
    edited_roster_name = f"{roster_name} Redigerad"
    template_name = f"PW PR0223 Sal {run_suffix}"
    edited_template_name = f"{template_name} Redigerad"
    api_responses: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()
        page.on("response", lambda response: _collect_api_response(api_responses, response))

        page.goto(f"{base_url}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Klassrumskartan", exact=True)).to_be_visible()
        _assert_final_guest_message(page)

        _create_roster(page, roster_name=roster_name)
        _edit_roster(page, edited_name=edited_roster_name)
        _select_overview_option_by_label(
            page,
            selector='[data-test="overview-roster-select"]',
            expected_label_fragment=edited_roster_name,
        )
        page.screenshot(path=str(artifacts_dir / "public-guest-roster-edited.png"), full_page=True)

        _create_template(page, template_name=template_name)
        _edit_template(page, edited_name=edited_template_name)
        _select_overview_option_by_label(
            page,
            selector='[data-test="overview-template-select"]',
            expected_label_fragment=edited_template_name,
        )
        _wait_for_guest_workspace_entry(page)
        page.screenshot(
            path=str(artifacts_dir / "public-guest-template-edited.png"), full_page=True
        )

        _assert_grouping_draft_continuity(page, artifacts_dir=artifacts_dir)
        _assert_seating_entry_and_continuity(
            page,
            expected_template_name=edited_template_name,
            artifacts_dir=artifacts_dir,
        )

        _delete_template(page)
        _delete_roster(page)

        _assert_final_guest_message(page)
        normalized_text = _normalize_visible_text(page)
        assert "Börja med att skapa en klasslista." in normalized_text
        assert "Behöver du mer vägledning kan du trycka på Hjälp." in normalized_text

        _assert_no_owner_scoped_api_calls(api_responses)

        page.screenshot(path=str(artifacts_dir / "public-guest-overview-final.png"), full_page=True)

        context.close()
        browser.close()

    network_artifact = {
        "public_route": f"{base_url}{PUBLIC_APP_PATH}",
        "blocked_owner_scoped_prefixes": list(BLOCKED_OWNER_SCOPED_PREFIXES),
        "api_responses": api_responses,
    }
    (artifacts_dir / "network-audit.json").write_text(
        json.dumps(network_artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"playwright-pr-0223-public-guest-checkpoint3: ok -> {artifacts_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
