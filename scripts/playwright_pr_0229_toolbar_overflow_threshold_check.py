"""Focused Playwright proof for PR-0229 planner shell and toolbar thresholds.

This targeted script verifies two live responsive contracts for the classroom
planner:

1. The authenticated planner shell keeps the left sidebar collapsed until the
   route reaches its wider desktop breakpoint.
2. Within one monotonic width segment, the toolbar moves lower-priority
   controls into overflow in the intended order.

It checks authenticated and public-guest grouping/seating workspaces and
records just-above / just-below evidence as JSON plus screenshots.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Literal

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    create_roster,
    create_template,
    login_to_app,
    open_class_workspace,
    open_grouping_workspace,
    open_seating_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0229-toolbar-overflow-thresholds")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
IMPORT_FILE = Path("data/class_list_example_inputs/sa24d_klasslista_komma.txt")

WorkspaceKind = Literal["grouping", "seating"]


def _parse_args() -> argparse.Namespace:
    """Parse CLI args for the focused overflow threshold proof."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Base URL for the SPA host (default: http://127.0.0.1:5173).",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=str(ARTIFACTS_DIR),
        help="Artifacts output directory.",
    )
    return parser.parse_args()


def _set_viewport(page: Page, *, width: int, height: int = 900) -> None:
    """Resize the page and wait for the toolbar stage to settle."""

    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(150)


def _toolbar_snapshot(page: Page, *, workspace: WorkspaceKind) -> dict[str, object]:
    """Read the live toolbar state through the shipped overflow data contract."""

    action_bar_test_id = (
        "grouping-actions-menu" if workspace == "grouping" else "seating-actions-menu"
    )
    result = page.locator('[data-ui="planner-workspace-action-bar"]').first.evaluate(
        """(element, workspace) => {
          const readInt = (name) => {
            const raw = element.getAttribute(name);
            return raw ? Number.parseInt(raw, 10) : null;
          };
          const root = document;
          const has = (selector) => root.querySelector(selector) !== null;
          return {
            stage: element.getAttribute('data-overflow-stage'),
            hiddenActions: (element.getAttribute('data-overflow-hidden-actions') ?? '')
              .split(',')
              .filter(Boolean),
            barClientWidth: element.clientWidth,
            barScrollWidth: element.scrollWidth,
            undoRedoInlineMinWidthPx: readInt('data-overflow-undo-redo-inline-min-width'),
            resetInlineMinWidthPx: readInt('data-overflow-reset-inline-min-width'),
            newDraftInlineMinWidthPx: readInt('data-overflow-new-draft-inline-min-width'),
            contextInlineMinWidthPx: readInt('data-overflow-context-inline-min-width'),
            smartInlineMinWidthPx: readInt('data-overflow-smart-inline-min-width'),
            undoInlineVisible: workspace === 'grouping'
              ? has('[data-test="grouping-undo-redo-cluster"]')
              : has('[data-test="seating-undo-redo-cluster"]'),
            resetInlineVisible: workspace === 'grouping'
              ? has('[data-test="reset-grouping-draft"]')
              : has('[data-test="reset-seating-draft"]'),
            newDraftInlineVisible: workspace === 'grouping'
              ? has('[data-test="new-grouping-draft"]')
              : has('[data-test="new-seating-draft"]'),
            contextInlineVisible: workspace === 'grouping'
              ? has('[data-test="grouping-roster-control"]')
              : has('[data-test="seating-workspace-setup"]'),
            smartInlineVisible: workspace === 'grouping'
              ? has('[data-test="grouping-smart-cluster"]')
              : has('[data-test="seating-smart-cluster"]'),
            actionsMenuVisible: has(
              workspace === 'grouping'
                ? '[data-test="grouping-actions-menu"]'
                : '[data-test="seating-actions-menu"]'
            ),
          };
        }""",
        workspace,
    )
    assert result["actionsMenuVisible"], f"{action_bar_test_id} did not render."
    return result


def _stabilize_toolbar_snapshot(
    page: Page,
    *,
    workspace: WorkspaceKind,
    attempts: int = 10,
    delay_ms: int = 60,
) -> dict[str, object]:
    """Wait until the toolbar overflow state stops changing after a resize."""

    previous_key: tuple[object, ...] | None = None
    snapshot = _toolbar_snapshot(page, workspace=workspace)
    for _ in range(attempts):
        snapshot = _toolbar_snapshot(page, workspace=workspace)
        key = (
            tuple(snapshot["hiddenActions"]),
            snapshot["stage"],
            snapshot["barClientWidth"],
            snapshot["barScrollWidth"],
        )
        if key == previous_key:
            return snapshot
        previous_key = key
        page.wait_for_timeout(delay_ms)
    return snapshot


def _shell_snapshot(page: Page) -> dict[str, object]:
    """Read the planner auth-shell state that affects available toolbar width."""

    return page.locator("body").evaluate(
        """() => {
          const wrapper = document.querySelector('.auth-main-wrapper');
          const header = document.querySelector('.auth-mobile-header');
          const readMargin = () => {
            if (!(wrapper instanceof HTMLElement)) {
              return null;
            }
            return Number.parseFloat(window.getComputedStyle(wrapper).marginLeft || '0');
          };
          const isVisible = (element) => {
            if (!(element instanceof HTMLElement)) {
              return false;
            }
            const style = window.getComputedStyle(element);
            return style.display !== 'none' && style.visibility !== 'hidden';
          };
          return {
            wrapperMarginLeftPx: readMargin(),
            mobileHeaderVisible: isVisible(header),
          };
        }""",
    )


def _open_actions_menu(page: Page, *, workspace: WorkspaceKind) -> None:
    """Open the shared toolbar overflow/actions menu."""

    trigger = (
        page.locator('[data-test="grouping-actions-menu"]')
        if workspace == "grouping"
        else page.locator('[data-test="seating-actions-menu"]')
    )
    expect(trigger).to_be_visible()
    trigger.click()


def _menu_item_state(page: Page, *, workspace: WorkspaceKind) -> dict[str, bool]:
    """Return which overflow-only planner actions are currently present in the menu."""

    prefix = "grouping" if workspace == "grouping" else "seating"
    return {
        "undo": page.locator(f'[data-test="{prefix}-overflow-undo"]').count() > 0,
        "redo": page.locator(f'[data-test="{prefix}-overflow-redo"]').count() > 0,
        "reset": page.locator(f'[data-test="{prefix}-overflow-reset"]').count() > 0,
        "newDraft": page.locator(f'[data-test="{prefix}-overflow-new-draft"]').count() > 0,
        "context": page.locator(
            f'[data-test="{prefix}-overflow-{"roster-control" if workspace == "grouping" else "template-control"}"]'
        ).count()
        > 0,
        "smart": page.locator(f'[data-test="{prefix}-overflow-smart-control"]').count() > 0,
    }


def _close_actions_menu(page: Page) -> None:
    """Dismiss the open toolbar menu so later mode switches are not obstructed."""

    page.keyboard.press("Escape")
    page.wait_for_timeout(100)


def _find_smallest_width_for_predicate(
    page: Page,
    *,
    predicate,
    low: int,
    high: int,
    workspace: WorkspaceKind | None = None,
    snapshot_factory=None,
) -> int:
    """Binary-search the smallest viewport width that satisfies a monotonic predicate."""

    if snapshot_factory is None:
        assert workspace is not None

        def default_snapshot_factory() -> dict[str, object]:
            return _stabilize_toolbar_snapshot(page, workspace=workspace)

        snapshot_factory = default_snapshot_factory

    original_high = high
    _set_viewport(page, width=high)
    assert predicate(snapshot_factory())
    _set_viewport(page, width=low)
    assert not predicate(snapshot_factory())

    left = low
    right = high
    while left + 1 < right:
        middle = (left + right) // 2
        _set_viewport(page, width=middle)
        if predicate(snapshot_factory()):
            right = middle
        else:
            left = middle

    candidate = right
    _set_viewport(page, width=candidate)
    while not predicate(snapshot_factory()):
        candidate += 1
        if candidate > original_high:
            raise AssertionError("Failed to recover a stable true viewport after binary search.")
        _set_viewport(page, width=candidate)

    while candidate - 1 >= low:
        _set_viewport(page, width=candidate - 1)
        if predicate(snapshot_factory()):
            candidate -= 1
            continue
        break

    return candidate


def _verify_auth_shell_breakpoint(
    page: Page,
    *,
    label: str,
    artifacts_dir: Path,
) -> dict[str, object]:
    """Capture the exact auth-shell viewport where the desktop sidebar pins."""

    desktop_sidebar_viewport_min_width = _find_smallest_width_for_predicate(
        page,
        predicate=lambda snapshot: snapshot["mobileHeaderVisible"] is False,
        low=700,
        high=1500,
        snapshot_factory=lambda: _shell_snapshot(page),
    )

    _set_viewport(page, width=desktop_sidebar_viewport_min_width)
    page.wait_for_timeout(450)
    desktop_snapshot = _shell_snapshot(page)
    assert desktop_snapshot["mobileHeaderVisible"] is False
    assert (desktop_snapshot["wrapperMarginLeftPx"] or 0) >= 200

    _set_viewport(page, width=desktop_sidebar_viewport_min_width - 1)
    page.wait_for_timeout(450)
    compact_snapshot = _shell_snapshot(page)
    assert compact_snapshot["mobileHeaderVisible"] is True
    assert (compact_snapshot["wrapperMarginLeftPx"] or 0) <= 1

    page.screenshot(
        path=str(artifacts_dir / f"{label}-shell-compact.png"),
        full_page=True,
    )

    return {
        "desktopSidebarViewportMinWidthPx": desktop_sidebar_viewport_min_width,
        "compactDesktopViewportMaxWidthPx": desktop_sidebar_viewport_min_width - 1,
        "desktopSnapshot": desktop_snapshot,
        "compactSnapshot": compact_snapshot,
    }


def _verify_workspace_thresholds(
    page: Page,
    *,
    label: str,
    workspace: WorkspaceKind,
    artifacts_dir: Path,
    search_high: int = 1500,
) -> dict[str, object]:
    """Capture exact just-above / just-below viewport cutoffs for one live workspace."""
    contribution_order = ["undo-redo", "reset", "new-draft", "context", "smart"]
    expected_menu_key = {
        "undo-redo": "undo",
        "reset": "reset",
        "new-draft": "newDraft",
        "context": "context",
        "smart": "smart",
    }
    threshold_results: dict[str, object] = {}
    _set_viewport(page, width=search_high)
    current_width = search_high
    previous_snapshot = _stabilize_toolbar_snapshot(page, workspace=workspace)
    assert previous_snapshot["hiddenActions"] == []

    for index, contribution_id in enumerate(contribution_order):
        expected_hidden_actions = contribution_order[: index + 1]
        threshold_name = contribution_id.replace("-", "_")
        overflow_snapshot: dict[str, object] | None = None

        while current_width > 400:
            current_width -= 1
            page.set_viewport_size({"width": current_width, "height": 900})
            page.wait_for_timeout(25)
            candidate_snapshot = _toolbar_snapshot(page, workspace=workspace)
            if candidate_snapshot["hiddenActions"] == previous_snapshot["hiddenActions"]:
                continue

            candidate_snapshot = _stabilize_toolbar_snapshot(
                page, workspace=workspace, attempts=6, delay_ms=40
            )
            if candidate_snapshot["hiddenActions"] == previous_snapshot["hiddenActions"]:
                continue

            if candidate_snapshot["hiddenActions"] != expected_hidden_actions:
                continue

            overflow_snapshot = candidate_snapshot
            break

        if overflow_snapshot is None:
            raise AssertionError(f"{label} never transitioned {contribution_id} into overflow.")

        threshold_width = current_width + 1
        inline_snapshot = previous_snapshot
        assert contribution_id not in inline_snapshot["hiddenActions"]

        _open_actions_menu(page, workspace=workspace)
        menu_state = _menu_item_state(page, workspace=workspace)
        _close_actions_menu(page)
        if contribution_id == "undo-redo":
            assert menu_state["undo"] and menu_state["redo"], (
                f"{label} expected overflow affordances for undo/redo at {current_width}px."
            )
        else:
            assert menu_state[expected_menu_key[contribution_id]], (
                f"{label} expected overflow affordance for {contribution_id} at {current_width}px."
            )

        threshold_results[threshold_name] = {
            "inlineViewportMinWidthPx": threshold_width,
            "inlineSnapshot": inline_snapshot,
            "overflowViewportWidthPx": current_width,
            "overflowSnapshot": overflow_snapshot,
            "menuState": menu_state,
        }
        previous_snapshot = overflow_snapshot

    _set_viewport(page, width=threshold_results["smart"]["overflowViewportWidthPx"])
    _open_actions_menu(page, workspace=workspace)
    page.screenshot(
        path=str(artifacts_dir / f"{label}-smart-overflow.png"),
        full_page=True,
    )
    _close_actions_menu(page)

    return threshold_results


def _public_wait_for_overview(page: Page) -> None:
    """Wait for the browser-owned guest overview shell to render."""

    expect(page.locator('[data-test="overview-roster-select"]')).to_be_visible(timeout=60000)
    expect(page.locator('[data-test="overview-template-select"]')).to_be_visible(timeout=60000)


def _public_create_roster(page: Page, *, roster_name: str) -> None:
    """Create one public guest roster through the import-preview flow."""

    page.get_by_role("button", name=re.compile(r"Ny klasslista", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.locator('input[type="file"]').first.set_input_files(str(IMPORT_FILE))
    expect(page.locator('[data-test="roster-import-summary"]')).to_be_visible(timeout=60000)
    page.get_by_label("Klassens namn").fill(roster_name)
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    expect(page.locator('[data-test="overview-roster-select"]')).to_have_value(re.compile(r".+"))


def _public_create_template(page: Page, *, template_name: str) -> None:
    """Create one tiny public guest classroom."""

    page.get_by_role("button", name=re.compile(r"Nytt klassrum", re.IGNORECASE)).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)
    page.get_by_role("button", name=re.compile(r"Sittplats", re.IGNORECASE)).click()
    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    expect(grid_buttons.nth(0)).to_be_visible()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()
    page.get_by_role("button", name=re.compile(r"Skapa klassrum", re.IGNORECASE)).click()
    expect(page.locator('[data-test="overview-template-select"]')).to_have_value(re.compile(r".+"))


def _public_open_mode(page: Page, *, mode: Literal["grouping", "seating"]) -> None:
    """Open one guest planner workspace from the shared top-panel toggle."""

    page.locator(f'[data-test="planner-mode-{mode}"]').last.click(force=True)
    if mode == "grouping":
        expect(page.locator('[data-test="new-grouping-draft"]')).to_be_visible(timeout=10000)
    else:
        expect(page.locator('[data-test="seating-template-select"]')).to_be_visible(timeout=10000)


def main() -> None:
    """Run the focused live threshold proof and write JSON artifacts."""

    args = _parse_args()
    config = get_config(["--base-url", args.base_url])
    base_url = args.base_url.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    auth_roster_name = f"PR-0229 Auth Klass {run_suffix}"
    auth_template_name = f"PR-0229 Auth Sal {run_suffix}"
    guest_roster_name = f"PR-0229 Gästklass {run_suffix}"
    guest_template_name = f"PR-0229 Gästrum {run_suffix}"

    results: dict[str, object] = {}

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)

        auth_context = browser.new_context(viewport={"width": 1440, "height": 900})
        auth_page = auth_context.new_page()
        login_to_app(auth_page, base_url=base_url, email=config.email, password=config.password)
        create_roster(auth_page, roster_name=auth_roster_name)
        create_template(auth_page, template_name=auth_template_name)
        open_class_workspace(auth_page, roster_name=auth_roster_name)
        open_grouping_workspace(auth_page, template_name=auth_template_name)
        auth_grouping_shell = _verify_auth_shell_breakpoint(
            auth_page,
            label="auth-grouping",
            artifacts_dir=artifacts_dir,
        )
        results["auth_grouping"] = {
            "shell": auth_grouping_shell,
            "toolbar": _verify_workspace_thresholds(
                auth_page,
                label="auth-grouping",
                workspace="grouping",
                artifacts_dir=artifacts_dir,
                search_high=auth_grouping_shell["compactDesktopViewportMaxWidthPx"],
            ),
        }
        _set_viewport(auth_page, width=1440)
        open_seating_workspace(auth_page, template_name=auth_template_name)
        auth_seating_shell = _verify_auth_shell_breakpoint(
            auth_page,
            label="auth-seating",
            artifacts_dir=artifacts_dir,
        )
        results["auth_seating"] = {
            "shell": auth_seating_shell,
            "toolbar": _verify_workspace_thresholds(
                auth_page,
                label="auth-seating",
                workspace="seating",
                artifacts_dir=artifacts_dir,
                search_high=auth_seating_shell["compactDesktopViewportMaxWidthPx"],
            ),
        }
        auth_context.close()

        guest_context = browser.new_context(viewport={"width": 1440, "height": 900})
        guest_page = guest_context.new_page()
        guest_page.goto(f"{base_url}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
        _public_wait_for_overview(guest_page)
        _public_create_roster(guest_page, roster_name=guest_roster_name)
        _public_create_template(guest_page, template_name=guest_template_name)
        _public_open_mode(guest_page, mode="grouping")
        results["guest_grouping"] = {
            "toolbar": _verify_workspace_thresholds(
                guest_page,
                label="guest-grouping",
                workspace="grouping",
                artifacts_dir=artifacts_dir,
            ),
        }
        _set_viewport(guest_page, width=1440)
        guest_page.locator('[data-test="planner-mode-overview"]').last.click(force=True)
        _public_wait_for_overview(guest_page)
        _public_open_mode(guest_page, mode="seating")
        results["guest_seating"] = {
            "toolbar": _verify_workspace_thresholds(
                guest_page,
                label="guest-seating",
                workspace="seating",
                artifacts_dir=artifacts_dir,
            ),
        }
        guest_context.close()
        browser.close()

    results_path = artifacts_dir / "threshold-results.json"
    results_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"playwright-pr-0229-toolbar-overflow-thresholds: ok -> {artifacts_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
