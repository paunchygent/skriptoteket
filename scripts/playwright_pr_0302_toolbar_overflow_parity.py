"""Playwright proof for PR-0302 planner toolbar overflow parity.

Purpose:
    Prove the Klassrumskartan grouping and seating toolbars keep one responsive
    overflow contract across authenticated and public guest shells. The proof
    performs a desktop -> tablet -> phone -> tablet -> desktop resize roundtrip
    and asserts the measured toolbar ladder, not just static viewport snapshots.

Relationships:
    - Reuses the signed local HuleEdu continuation lane for the authenticated
      shell.
    - Exercises the public browser-owned guest shell through the public route so
      phone-only assumptions cannot silently drift into authenticated behavior.
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    focus_workspace_mode,
    open_class_workspace,
    wait_for_app_heading,
)
from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import (
    DEFAULT_PROVIDER_SUBJECT,
    backend_url_for_spa,
    install_local_huleedu_auth_routes,
    new_private_key,
    public_key_pem,
    seed_huleedu_projection,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
    verify_profile_continuation_api,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0302-toolbar-overflow-parity")
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0302"
PROVIDER_EMAIL = "pr-0302-live-huleedu@example.test"
DISPLAY_NAME = "PR 0302 Teacher"

Surface = Literal["auth", "public"]
WorkspaceKind = Literal["grouping", "seating"]


@dataclass(frozen=True)
class ToolbarExpectation:
    label: str
    width: int
    height: int
    exact_hidden: tuple[str, ...] | None = None
    grouping_exact_hidden: tuple[str, ...] | None = None
    seating_exact_hidden: tuple[str, ...] | None = None


ROUNDTRIP = (
    ToolbarExpectation("desktop-start", 2048, 900, ()),
    ToolbarExpectation("laptop-down", 1366, 768),
    ToolbarExpectation("tablet-down", 768, 1024),
    ToolbarExpectation("phone-breakpoint", 767, 900, ()),
    ToolbarExpectation("phone-context-overflow", 520, 844, ("context",)),
    ToolbarExpectation("phone-settings-menu", 440, 844, ("context",)),
    ToolbarExpectation(
        "phone-reset-overflow",
        420,
        844,
        grouping_exact_hidden=("context", "reset"),
    ),
    ToolbarExpectation(
        "iphone-15-pro",
        393,
        852,
        grouping_exact_hidden=("context", "reset", "distribution"),
        seating_exact_hidden=("context", "reset"),
    ),
    ToolbarExpectation(
        "phone",
        390,
        844,
        grouping_exact_hidden=("context", "reset", "distribution"),
        seating_exact_hidden=("context", "reset"),
    ),
    ToolbarExpectation(
        "phone-distribution-overflow", 330, 844, ("context", "reset", "distribution")
    ),
    ToolbarExpectation(
        "phone-reset-return",
        420,
        844,
        grouping_exact_hidden=("context", "reset"),
    ),
    ToolbarExpectation("phone-settings-return", 440, 844, ("context",)),
    ToolbarExpectation("phone-context-return", 520, 844, ("context",)),
    ToolbarExpectation("tablet-up", 768, 1024),
    ToolbarExpectation("laptop-up", 1366, 768),
    ToolbarExpectation("desktop-end", 2048, 900, ()),
)
COLLAPSE_ORDER = ("context", "reset", "distribution")


def _is_local_vite_url(base_url: str) -> bool:
    """Return whether the proof is running against a local Vite host."""

    return "127.0.0.1" in base_url or "localhost" in base_url


def _visible(locator: Locator) -> bool:
    """Return whether at least one matching element is visible."""

    for index in range(locator.count()):
        if locator.nth(index).is_visible():
            return True
    return False


def _first_visible(page: Page, selector: str) -> Locator:
    """Return the first visible locator matching a selector."""

    locator = page.locator(selector)
    for _ in range(40):
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                return candidate
        page.wait_for_timeout(100)
    raise AssertionError(f"No visible element matched {selector!r}.")


def _wait_for_select_option(page: Page, *, selector: str, label: str) -> str:
    """Wait for a select option containing a label and return its value."""

    selects = page.locator(selector)
    for _ in range(50):
        for index in range(selects.count()):
            select = selects.nth(index)
            if not select.is_visible():
                continue
            option_rows = select.evaluate(
                """element => Array.from(element.options).map(option => ({
                    value: option.value,
                    label: option.label,
                }))"""
            )
            for option in option_rows:
                if option["value"] and label in option["label"]:
                    return str(option["value"])
        page.wait_for_timeout(200)
    raise AssertionError(f"{label!r} did not appear in {selector!r}.")


def _create_roster(page: Page, *, roster_name: str) -> None:
    """Create one class list through whichever overview shell is visible."""

    _first_visible(
        page, '[data-test="overview-create-roster"], [data-test="phone-overview-create-roster"]'
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Ny klasslista", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Klass 9A", re.IGNORECASE)).fill(roster_name)
    page.locator("textarea").fill("Ada Lovelace\nBo Berg\nCecilia Ceder\nDavid Dahl")
    page.get_by_role("button", name=re.compile(r"Skapa klasslista", re.IGNORECASE)).click()
    _wait_for_select_option(
        page,
        selector='[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]',
        label=roster_name,
    )


def _create_template(page: Page, *, template_name: str) -> None:
    """Create one small room through whichever overview shell is visible."""

    _first_visible(
        page, '[data-test="overview-create-template"], [data-test="phone-overview-create-template"]'
    ).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Nytt klassrum", re.IGNORECASE))
    ).to_be_visible()
    page.get_by_placeholder(re.compile(r"Sal 304", re.IGNORECASE)).fill(template_name)

    grid_buttons = page.locator("section .relative.grid.gap-1 button[type='button']")
    expect(grid_buttons.nth(0)).to_be_visible()
    grid_buttons.nth(0).click()
    grid_buttons.nth(1).click()

    page.get_by_role("button", name=re.compile(r"Skapa(?: klassrum)?", re.IGNORECASE)).click()
    _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )


def _select_overview_assets(page: Page, *, roster_name: str, template_name: str) -> None:
    """Select the seeded class list and classroom in the overview shell."""

    roster_value = _wait_for_select_option(
        page,
        selector='[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]',
        label=roster_name,
    )
    template_value = _wait_for_select_option(
        page,
        selector='[data-test="overview-template-select"], [data-test="phone-overview-template-select"]',
        label=template_name,
    )

    roster_select = _first_visible(
        page, '[data-test="overview-roster-select"], [data-test="phone-overview-roster-select"]'
    )
    template_select = _first_visible(
        page, '[data-test="overview-template-select"], [data-test="phone-overview-template-select"]'
    )
    roster_select.select_option(value=roster_value)
    template_select.select_option(value=template_value)
    expect(roster_select).to_have_value(roster_value)
    expect(template_select).to_have_value(template_value)


def _open_grouping_workspace(page: Page, *, template_name: str) -> None:
    """Open grouping and select the shared classroom context."""

    focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()

    page.locator('[data-test="grouping-actions-menu"]').click()
    page.locator('[data-test="grouping-overflow-open-settings"]').click()

    drawer = page.locator('[data-test="grouping-settings-drawer"]')
    expect(drawer).to_be_visible()
    template_select = drawer.locator('[data-test="grouping-settings-template-select"]')
    template_value = _wait_for_select_option(
        page,
        selector='[data-test="grouping-settings-template-select"]',
        label=template_name,
    )
    template_select.select_option(value=template_value)
    expect(template_select).to_have_value(template_value)
    page.keyboard.press("Escape")
    expect(drawer).not_to_be_visible()


def _open_seating_workspace(page: Page, *, template_name: str) -> None:
    """Open seating and select the shared classroom context."""

    focus_workspace_mode(page, label="Sittplatser")
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
    setup_surface = _first_visible(page, '[data-test="seating-workspace-setup"]')
    template_select = setup_surface.get_by_role("combobox")
    template_value = _wait_for_select_option(
        page,
        selector='[data-test="seating-template-select"]',
        label=template_name,
    )
    template_select.select_option(value=template_value)
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _start_grouping_draft(page: Page) -> None:
    """Start or refresh one grouping draft without depending on persistence lane shape."""

    page.locator('[data-test="new-grouping-draft"]').click()
    _first_visible(
        page, '[data-test="grouping-layout-lane"], [data-test="phone-grouping-workspace"]'
    )


def _start_seating_draft(page: Page) -> None:
    """Start one seating draft without depending on persistence lane shape."""

    page.locator('[data-test="new-seating-draft"]').click()
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible()


def _assert_box_inside(
    toolbar_box: dict[str, float], child_box: dict[str, float], *, label: str
) -> None:
    """Assert a child control stays inside the action bar bounds."""

    left_slop = child_box["x"] - toolbar_box["x"]
    right_slop = (toolbar_box["x"] + toolbar_box["width"]) - (child_box["x"] + child_box["width"])
    if left_slop < -1 or right_slop < -1:
        raise AssertionError(
            f"{label} escapes toolbar bounds: left={left_slop}, right={right_slop}."
        )


def _assert_toolbar_scroll_fit(page: Page, *, kind: WorkspaceKind) -> Locator:
    """Assert the visible toolbar has no horizontal overflow or detached controls."""

    toolbar = _first_visible(page, '[data-ui="planner-workspace-action-bar"]')
    scroll_state = toolbar.evaluate(
        """element => ({
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth,
        })"""
    )
    if scroll_state["scrollWidth"] > scroll_state["clientWidth"] + 2:
        raise AssertionError(f"{kind} toolbar overflows horizontally: {scroll_state}.")

    toolbar_box = toolbar.bounding_box()
    menu_box = page.locator(f'[data-test="{kind}-actions-menu"]').bounding_box()
    if toolbar_box is None or menu_box is None:
        raise AssertionError(f"Missing {kind} toolbar or overflow trigger box.")
    _assert_box_inside(toolbar_box, menu_box, label=f"{kind} overflow trigger")
    return toolbar


def _assert_menu_background(page: Page, *, kind: WorkspaceKind) -> None:
    """Assert the open overflow menu uses an opaque canvas-like background."""

    page.locator(f'[data-test="{kind}-actions-menu"]').click()
    menu = page.get_by_role("menu").last
    expect(menu).to_be_visible()
    background = menu.evaluate("element => getComputedStyle(element).backgroundColor")
    rgba_match = re.fullmatch(r"rgba\([^,]+,\s*[^,]+,\s*[^,]+,\s*([0-9.]+)\)", background)
    if rgba_match and float(rgba_match.group(1)) < 1:
        raise AssertionError(f"{kind} overflow menu background is translucent: {background}.")
    if background in {"transparent", "rgba(0, 0, 0, 0)"}:
        raise AssertionError(f"{kind} overflow menu background is transparent: {background}.")


def _close_menu(page: Page) -> None:
    page.keyboard.press("Escape")
    expect(page.get_by_role("menu")).not_to_be_visible()


def _selectors(kind: WorkspaceKind) -> dict[str, str]:
    if kind == "grouping":
        return {
            "context_inline": '[data-test="grouping-roster-control"]',
            "context_overflow": '[data-test="grouping-overflow-roster-control"]',
            "settings_overflow": '[data-test="grouping-overflow-open-settings"]',
            "reset_inline": '[data-test="reset-grouping-draft"]',
            "reset_overflow": '[data-test="grouping-overflow-reset"]',
            "distribution_inline": '[data-test="grouping-share-trigger"]',
            "distribution_overflow": '[data-test="grouping-overflow-share-trigger"]',
        }
    return {
        "context_inline": '[data-test="seating-workspace-setup"]',
        "context_overflow": '[data-test="seating-overflow-template-control"]',
        "settings_overflow": '[data-test="seating-overflow-open-settings"]',
        "reset_inline": '[data-test="reset-seating-draft"]',
        "reset_overflow": '[data-test="seating-overflow-reset"]',
        "distribution_inline": '[data-test="seating-share-trigger"]',
        "distribution_overflow": '[data-test="seating-overflow-share-trigger"]',
    }


def _read_hidden_actions(toolbar: Locator) -> tuple[str, ...]:
    """Read hidden contribution ids from the visible action bar."""

    raw_value = toolbar.get_attribute("data-overflow-hidden-actions") or ""
    if not raw_value:
        return ()
    return tuple(item for item in raw_value.split(",") if item)


def _toolbar_diagnostics(toolbar: Locator) -> dict[str, object]:
    """Return toolbar overflow diagnostics for assertion failures."""

    return toolbar.evaluate(
        """element => ({
            viewportWidth: window.innerWidth,
            phoneMediaMatches: window.matchMedia("(max-width: 767px)").matches,
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth,
            stage: element.getAttribute("data-overflow-stage"),
            hiddenActions: element.getAttribute("data-overflow-hidden-actions"),
            contextThreshold: element.getAttribute("data-overflow-context-inline-min-width"),
            resetThreshold: element.getAttribute("data-overflow-reset-inline-min-width"),
            distributionThreshold: element.getAttribute("data-overflow-distribution-inline-min-width"),
            inlineHidden: Array.from(element.querySelectorAll("[data-overflow-contribution]"))
                .map(node => ({
                    contribution: node.getAttribute("data-overflow-contribution"),
                    hidden: node.getAttribute("data-overflow-inline-hidden"),
                    className: node.getAttribute("class"),
                    width: node.getBoundingClientRect().width,
                })),
        })"""
    )


def _assert_allowed_prefix(hidden_actions: tuple[str, ...], *, kind: WorkspaceKind) -> None:
    """Assert the toolbar collapse state follows the approved priority prefix."""

    expected_prefix = COLLAPSE_ORDER[: len(hidden_actions)]
    if hidden_actions != expected_prefix:
        raise AssertionError(
            f"{kind} toolbar hidden actions are not a priority prefix: "
            f"actual={hidden_actions}, expected_prefix={expected_prefix}."
        )


def _assert_toolbar_placement(
    page: Page,
    *,
    surface: Surface,
    kind: WorkspaceKind,
    expectation: ToolbarExpectation,
) -> tuple[str, ...]:
    """Assert one toolbar placement state after a viewport resize."""

    page.set_viewport_size({"width": expectation.width, "height": expectation.height})
    exact_hidden = (
        expectation.grouping_exact_hidden
        if kind == "grouping" and expectation.grouping_exact_hidden is not None
        else expectation.seating_exact_hidden
        if kind == "seating" and expectation.seating_exact_hidden is not None
        else expectation.exact_hidden
    )
    hidden_actions: tuple[str, ...] = ()
    toolbar = _assert_toolbar_scroll_fit(page, kind=kind)
    stable_reads = 0
    last_hidden_actions: tuple[str, ...] | None = None
    for _ in range(30):
        toolbar = _assert_toolbar_scroll_fit(page, kind=kind)
        current_hidden_actions = _read_hidden_actions(toolbar)
        if current_hidden_actions == last_hidden_actions:
            stable_reads += 1
        else:
            stable_reads = 1
            last_hidden_actions = current_hidden_actions
        hidden_actions = current_hidden_actions
        if exact_hidden is not None and hidden_actions != exact_hidden:
            page.wait_for_timeout(250)
            continue
        if stable_reads < 2:
            page.wait_for_timeout(250)
            continue
        _assert_allowed_prefix(hidden_actions, kind=kind)
        break
    else:
        diagnostics = _toolbar_diagnostics(toolbar)
        raise AssertionError(
            f"{kind} toolbar did not reach expected hidden actions at {expectation.label}: "
            f"expected={exact_hidden}, actual={hidden_actions}, diagnostics={diagnostics}."
        )

    selectors = _selectors(kind)
    inline_expectations = {
        "context": selectors["context_inline"],
        "reset": selectors["reset_inline"],
        "distribution": selectors["distribution_inline"],
    }
    overflow_expectations = {
        "context": selectors["context_overflow"],
        "reset": selectors["reset_overflow"],
        "distribution": selectors["distribution_overflow"],
    }

    for contribution, selector in inline_expectations.items():
        should_be_inline = contribution not in hidden_actions
        if should_be_inline:
            if not _visible(page.locator(selector)):
                raise AssertionError(
                    f"{surface} {kind} {expectation.label} missing inline {contribution}: "
                    f"hidden={hidden_actions}, diagnostics={_toolbar_diagnostics(toolbar)}."
                )
        elif _visible(page.locator(selector)):
            raise AssertionError(
                f"{surface} {kind} {expectation.label} shows inline {contribution} despite overflow: "
                f"hidden={hidden_actions}, diagnostics={_toolbar_diagnostics(toolbar)}."
            )

    _assert_menu_background(page, kind=kind)
    settings_item = page.locator(selectors["settings_overflow"])
    if not _visible(settings_item) or "Avancerade inställningar" not in settings_item.inner_text():
        raise AssertionError(
            f"{surface} {kind} {expectation.label} missing advanced settings item: "
            f"hidden={hidden_actions}, diagnostics={_toolbar_diagnostics(toolbar)}."
        )
    for contribution, selector in overflow_expectations.items():
        should_be_overflowed = contribution in hidden_actions
        if should_be_overflowed and not _visible(page.locator(selector)):
            raise AssertionError(
                f"{surface} {kind} {expectation.label} missing overflow {contribution}: "
                f"hidden={hidden_actions}, diagnostics={_toolbar_diagnostics(toolbar)}."
            )
        if not should_be_overflowed and _visible(page.locator(selector)):
            raise AssertionError(
                f"{surface} {kind} {expectation.label} shows overflow {contribution} while inline: "
                f"hidden={hidden_actions}, diagnostics={_toolbar_diagnostics(toolbar)}."
            )
    page.screenshot(
        path=str(ARTIFACTS_DIR / f"{surface}-{kind}-{expectation.label}.png"),
        full_page=True,
    )
    _close_menu(page)
    return hidden_actions


def _assert_roundtrip(page: Page, *, surface: Surface, kind: WorkspaceKind) -> None:
    """Assert one workspace survives the full resize roundtrip."""

    hidden_steps: list[tuple[int, int]] = []
    for expectation in ROUNDTRIP:
        hidden_actions = _assert_toolbar_placement(
            page,
            surface=surface,
            kind=kind,
            expectation=expectation,
        )
        hidden_steps.append((expectation.width, len(hidden_actions)))

    for (previous_width, previous_length), (current_width, current_length) in zip(
        hidden_steps,
        hidden_steps[1:],
    ):
        if current_width < previous_width and current_length - previous_length > 1:
            raise AssertionError(
                f"{surface} {kind} toolbar overflow jumps by more than one contribution while narrowing: {hidden_steps}."
            )


def _prepare_workspace(
    page: Page,
    *,
    surface: Surface,
    roster_name: str,
    template_name: str,
) -> None:
    """Seed and open grouping/seating workspaces for one app surface."""

    _create_roster(page, roster_name=roster_name)
    _create_template(page, template_name=template_name)
    _select_overview_assets(page, roster_name=roster_name, template_name=template_name)

    if surface == "auth":
        open_class_workspace(page, roster_name=roster_name)

    _open_grouping_workspace(page, template_name=template_name)
    _start_grouping_draft(page)
    _assert_roundtrip(page, surface=surface, kind="grouping")

    _open_seating_workspace(page, template_name=template_name)
    _start_seating_draft(page)
    _assert_roundtrip(page, surface=surface, kind="seating")


def _run_auth_surface(
    page: Page,
    *,
    base_url: str,
    roster_name: str,
    template_name: str,
) -> None:
    """Open and prove the authenticated planner shell."""

    page.goto(f"{base_url.rstrip('/')}{APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)
    _prepare_workspace(
        page,
        surface="auth",
        roster_name=roster_name,
        template_name=template_name,
    )


def _run_public_surface(
    page: Page,
    *,
    base_url: str,
    roster_name: str,
    template_name: str,
) -> None:
    """Open and prove the public guest planner shell."""

    page.goto(f"{base_url.rstrip('/')}{PUBLIC_APP_PATH}", wait_until="domcontentloaded")
    wait_for_app_heading(page)
    _prepare_workspace(
        page,
        surface="public",
        roster_name=roster_name,
        template_name=template_name,
    )


def _run(
    *,
    base_url: str,
    backend_base_url: str,
    private_key: RSAPrivateKey,
) -> None:
    """Run authenticated and public toolbar parity proof against one stack."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_suffix = str(int(time.time()))
    local_user_id = seed_huleedu_projection(
        local_user_id=str(uuid4()),
        provider_subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
        jti=f"pr-0302-toolbar-overflow-{run_suffix}",
    )

    with sync_playwright() as playwright:
        verify_profile_continuation_api(
            playwright,
            backend_url=backend_base_url,
            signed_headers=signed_headers,
            local_user_id=local_user_id,
        )
        browser = launch_chromium(playwright)

        auth_context = browser.new_context(viewport={"width": 1440, "height": 900})
        auth_page = auth_context.new_page()
        if _is_local_vite_url(base_url):
            install_local_huleedu_auth_routes(
                auth_page,
                base_url=base_url,
                signed_headers=signed_headers,
                provider_subject=PROVIDER_SUBJECT,
                provider_email=PROVIDER_EMAIL,
                display_name=DISPLAY_NAME,
            )
        _run_auth_surface(
            auth_page,
            base_url=base_url,
            roster_name=f"PR0302 Auth Klass {run_suffix}",
            template_name=f"PR0302 Auth Sal {run_suffix}",
        )
        auth_context.close()

        public_context = browser.new_context(viewport={"width": 1440, "height": 900})
        public_page = public_context.new_page()
        _run_public_surface(
            public_page,
            base_url=base_url,
            roster_name=f"PR0302 Public Klass {run_suffix}",
            template_name=f"PR0302 Public Sal {run_suffix}",
        )
        public_context.close()

        browser.close()

    print(f"pr-0302-toolbar-overflow-parity: ok artifacts={ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the toolbar overflow parity proof."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--start-vite", action="store_true")
    proof_args, config_argv = parser.parse_known_args(argv)

    config = get_config(config_argv)
    private_key = new_private_key()
    public_key = public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_base_url: str) -> None:
        _run(
            base_url=base_url.rstrip("/"),
            backend_base_url=backend_base_url.rstrip("/"),
            private_key=private_key,
        )

    if proof_args.start_backend:
        with temporary_backend_server(
            public_key,
            artifacts_dir=ARTIFACTS_DIR,
            port=None if proof_args.start_vite else 8000,
        ) as live_backend:
            if proof_args.start_vite:
                with temporary_vite_server(proxy_target=live_backend) as live_base:
                    run_with_base_url(live_base, live_backend)
                return
            run_with_base_url(config.base_url, live_backend)
        return

    if proof_args.start_vite:
        with temporary_vite_server() as live_base:
            run_with_base_url(live_base, backend_url_for_spa(live_base))
        return

    run_with_base_url(config.base_url, backend_url_for_spa(config.base_url))


if __name__ == "__main__":  # pragma: no cover
    main()
