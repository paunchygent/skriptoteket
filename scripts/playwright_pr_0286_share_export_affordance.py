"""Playwright proof for PR-0286 share/export affordance consolidation.

Purpose:
    Exercise the live Klassrumskartan grouping and seating workspaces through
    the local authenticated app-continuation lane and verify that outward
    distribution is entered through one `Dela` affordance. The proof is scoped
    to the toolbar composition introduced by PR-0286; export and share backend
    contracts remain covered by their existing flow tests and share-link proofs.

Relationships:
    - Reuses the shared Klassrumskartan Playwright helpers for auth, class, room,
      and workspace setup.
    - Complements `PlannerShareExportPanel.spec.ts` by proving the component is
      wired into both live workspace toolbars at phone and desktop viewports.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    APP_PATH,
    create_roster,
    create_template,
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
    open_grouping_workspace,
    open_seating_workspace,
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

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0286-share-export-affordance")
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0286"
PROVIDER_EMAIL = "pr-0286-live-huleedu@example.test"
DISPLAY_NAME = "PR 0286 Teacher"
VIEWPORTS = (
    (390, 844),
    (1366, 768),
    (1440, 900),
)
MOBILE_SCROLL_PROOF_SHARE_ROWS = 8


def _is_local_vite_url(base_url: str) -> bool:
    """Return whether the proof is running against a local Vite host."""

    return "127.0.0.1" in base_url or "localhost" in base_url


def _login_for_proof(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Open the planner through local app continuation or the hosted login path."""

    if _is_local_vite_url(base_url):
        page.goto(f"{base_url.rstrip('/')}{APP_PATH}", wait_until="domcontentloaded")
        wait_for_app_heading(page)
        return

    login_to_app(page, base_url=base_url, email=email, password=password)


def _start_grouping_draft(page: Page) -> None:
    """Create one grouping draft so the toolbar exposes distribution actions."""

    with page.expect_response(re.compile(r".*/drafts/grouping/new$")) as response_info:
        page.get_by_role(
            "button", name=re.compile(r"Nytt (grupputkast|utkast)", re.IGNORECASE)
        ).click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected grouping draft creation to succeed, got {response_info.value.status}"
        )
    expect(page.locator("input[type='text']").first).to_have_value("Grupp 1")


def _start_seating_draft(page: Page) -> None:
    """Create one seating draft so the toolbar exposes distribution actions."""

    with page.expect_response(re.compile(r".*/drafts/seating/new$")) as response_info:
        page.locator('[data-test="new-seating-draft"]').click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected seating draft creation to succeed, got {response_info.value.status}"
        )
    expect(page.locator('[data-test="seating-share-trigger"]')).to_be_visible()


def _close_panel(page: Page, *, kind: str) -> None:
    """Close the combined share/export panel after one viewport assertion."""

    page.keyboard.press("Escape")
    expect(page.locator(f'[data-test="{kind}-share-management"]')).not_to_be_visible()


def _ensure_mobile_overflow_content(panel: Locator, *, kind: str) -> None:
    """Create enough active share rows that the mobile sheet must scroll."""

    link_rows = panel.locator('[data-test^="planner-share-link-"]')
    create_button = panel.locator(f'[data-test="{kind}-share-create-mobile"]')
    while link_rows.count() < MOBILE_SCROLL_PROOF_SHARE_ROWS:
        expected_count = link_rows.count() + 1
        expect(create_button).to_be_enabled(timeout=30_000)
        create_button.click()
        expect(link_rows).to_have_count(expected_count, timeout=30_000)


def _wait_for_share_link_state(page: Page, panel: Locator) -> None:
    """Wait until share-link management has rendered either rows or empty state."""

    link_rows = panel.locator('[data-test^="planner-share-link-"]')
    empty_state = panel.locator('[data-test="planner-share-links-empty"]')
    for _ in range(40):
        if link_rows.count() > 0:
            expect(link_rows.first).to_be_visible()
            return
        if empty_state.count() > 0 and empty_state.first.is_visible():
            return
        page.wait_for_timeout(250)
    raise AssertionError("Share-link section did not render active rows or empty state.")


def _assert_equal_heights(*, rail: Locator, create_button: Locator, export_button: Locator) -> None:
    """Assert overview share/export controls share the same rendered height."""

    boxes = {
        "scope rail": rail.bounding_box(),
        "create link": create_button.bounding_box(),
        "export button": export_button.bounding_box(),
    }
    missing = [name for name, box in boxes.items() if box is None]
    if missing:
        raise AssertionError(f"Missing rendered boxes for: {', '.join(missing)}")

    heights = {name: round(box["height"], 2) for name, box in boxes.items() if box is not None}
    if max(heights.values()) - min(heights.values()) > 0.5:
        raise AssertionError(f"Overview share/export controls have uneven heights: {heights}")


def _assert_mobile_sheet_scroll_is_contained(page: Page, panel: Locator) -> None:
    """Assert the Dela sheet owns scrolling while background scroll stays fixed."""

    scroller = panel.locator('[data-test="planner-share-export-scroll"]')
    link_list = panel.locator('[data-test="planner-share-export-link-list"]')
    expect(scroller).to_be_visible()
    expect(page.locator('[data-test="planner-share-export-backdrop"]')).to_be_visible()

    body_overflow = page.evaluate("() => document.body.style.overflow")
    if body_overflow != "hidden":
        raise AssertionError(f"Expected body scroll lock while Dela is open, got {body_overflow!r}")

    initial_window_scroll = page.evaluate("() => window.scrollY")
    scroll_owner = scroller
    scroll_state = scroll_owner.evaluate(
        """(element) => {
            const maxScrollTop = element.scrollHeight - element.clientHeight;
            element.scrollTop = Math.max(1, Math.floor(maxScrollTop / 2));
            return {scrollTop: element.scrollTop, maxScrollTop};
        }"""
    )
    if scroll_state["maxScrollTop"] <= 0 and link_list.count() > 0:
        scroll_owner = link_list
        scroll_state = scroll_owner.evaluate(
            """(element) => {
                const maxScrollTop = element.scrollHeight - element.clientHeight;
                element.scrollTop = Math.max(1, Math.floor(maxScrollTop / 2));
                return {scrollTop: element.scrollTop, maxScrollTop};
            }"""
        )
    if scroll_state["maxScrollTop"] <= 0:
        raise AssertionError("Expected mobile Dela content to overflow a contained scroller.")
    if scroll_state["scrollTop"] <= 0:
        raise AssertionError("Expected mobile Dela contained scroller to move.")
    if page.evaluate("() => window.scrollY") != initial_window_scroll:
        raise AssertionError("Window scrolled while the Dela sheet scroller moved.")

    scroll_owner.evaluate("(element) => { element.scrollTop = element.scrollHeight; }")
    bottom_window_scroll = page.evaluate("() => window.scrollY")
    scroll_owner.hover()
    page.mouse.wheel(0, 1800)
    page.wait_for_timeout(150)
    if page.evaluate("() => window.scrollY") != bottom_window_scroll:
        raise AssertionError("Wheel scroll bled from the Dela sheet into the workspace.")


def _verify_distribution_panel(
    page: Page,
    *,
    kind: str,
    viewport_label: str,
    width: int,
    file_option_ids: tuple[str, ...],
) -> None:
    """Verify one workspace exposes file exports inside the combined Dela panel."""

    expect(page.locator(f'[data-test="{kind}-export-group"]')).to_have_count(0)
    expect(page.locator(f'[data-test="{kind}-export-default"]')).to_have_count(0)
    expect(page.locator(f'[data-test="{kind}-export-menu-trigger"]')).to_have_count(0)

    if width < 1024:
        page.locator(f'[data-test="{kind}-actions-menu"]').click()
        trigger = page.locator(f'[data-test="{kind}-overflow-share-trigger"]')
    else:
        trigger = page.locator(f'[data-test="{kind}-share-trigger"]')
    expect(trigger).to_be_visible()
    expect(trigger).to_contain_text("Dela")
    trigger.click()

    panel = page.locator(f'[data-test="{kind}-share-management"]')
    expect(panel).to_be_visible()
    expect(panel.get_by_role("heading", name="Dela och exportera")).to_be_visible()
    expect(panel.get_by_role("heading", name="Länk")).to_be_visible()
    expect(panel.get_by_role("heading", name="Filer")).to_be_visible()
    desktop_create = panel.locator(f'[data-test="{kind}-share-create"]')
    mobile_create = panel.locator(f'[data-test="{kind}-share-create-mobile"]')
    if width < 768:
        expect(desktop_create).to_be_hidden()
        expect(mobile_create).to_be_visible()
    else:
        expect(desktop_create).to_be_visible()
        expect(mobile_create).to_be_hidden()
    _wait_for_share_link_state(page, panel)

    for option_id in file_option_ids:
        option = panel.locator(f'[data-test="{kind}-export-option-{option_id}"]')
        expect(option).to_be_visible()
        expect(option).to_be_enabled()

    if width < 768:
        _ensure_mobile_overflow_content(panel, kind=kind)
        _assert_mobile_sheet_scroll_is_contained(page, panel)

    page.screenshot(
        path=str(ARTIFACTS_DIR / f"{kind}-{viewport_label}-share-export-panel.png"),
        full_page=True,
    )
    _close_panel(page, kind=kind)


def _verify_overview_scope_selector(
    page: Page,
    *,
    viewport_label: str,
    width: int,
    roster_name: str,
    template_name: str,
) -> None:
    """Verify the overview Dela selector rail and selected-draft confirmation."""

    focus_workspace_mode(page, label="Översikt")
    panel_prefix = "phone-overview" if width < 768 else "desktop-overview"
    panel = page.locator(f'[data-test="{panel_prefix}-share-export-panel"]')
    expect(panel).to_be_visible()
    expect(panel.get_by_role("heading", name="Dela och exportera")).to_be_visible()

    context = panel.locator('[data-test="planner-share-export-scope-context"]')
    meta = panel.locator('[data-test="planner-share-export-scope-meta"]')
    expect(context).to_have_text(f"{roster_name} · {template_name}")
    expect(meta).to_contain_text("Sittschema")

    panel.locator('[data-test="planner-share-export-scope-grouping"]').click()
    expect(context).to_have_text(f"{roster_name} · {template_name}")
    expect(meta).to_contain_text("Gruppindelning")
    expect(panel.locator('[data-test="planner-share-export-scope-seating"]')).to_be_enabled()

    if width >= 768:
        _assert_equal_heights(
            rail=panel.locator(".planner-share-export-scope-rail"),
            create_button=panel.locator(f'[data-test="{panel_prefix}-share-create"]'),
            export_button=panel.locator(f'[data-test="{panel_prefix}-export-option-xlsx"]'),
        )

    page.screenshot(
        path=str(ARTIFACTS_DIR / f"overview-{viewport_label}-share-export-scope-selector.png"),
        full_page=True,
    )


def _verify_viewport(
    page: Page,
    *,
    width: int,
    height: int,
    roster_name: str,
    template_name: str,
) -> None:
    """Verify grouping and seating share/export panels at one viewport size."""

    viewport_label = f"{width}x{height}"
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(250)

    _verify_overview_scope_selector(
        page,
        viewport_label=viewport_label,
        width=width,
        roster_name=roster_name,
        template_name=template_name,
    )

    focus_workspace_mode(page, label="Grupper")
    expect(page.locator('[data-test="grouping-actions-menu"]')).to_be_visible()
    _verify_distribution_panel(
        page,
        kind="grouping",
        viewport_label=viewport_label,
        width=width,
        file_option_ids=("xlsx", "pdf"),
    )

    focus_workspace_mode(page, label="Sittplatser")
    expect(page.locator('[data-test="seating-actions-menu"]')).to_be_visible()
    _verify_distribution_panel(
        page,
        kind="seating",
        viewport_label=viewport_label,
        width=width,
        file_option_ids=("a3", "a4", "xlsx"),
    )


def _run(
    *,
    base_url: str,
    backend_base_url: str,
    private_key: RSAPrivateKey,
    email: str,
    password: str,
) -> None:
    """Run the live PR-0286 toolbar proof against one stack."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_suffix = str(int(time.time()))
    roster_name = f"PR0286 Klass {run_suffix}"
    template_name = f"PR0286 Sal {run_suffix}"
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
        jti=f"pr-0286-share-export-affordance-{run_suffix}",
    )

    with sync_playwright() as playwright:
        verify_profile_continuation_api(
            playwright,
            backend_url=backend_base_url,
            signed_headers=signed_headers,
            local_user_id=local_user_id,
        )
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        if _is_local_vite_url(base_url):
            install_local_huleedu_auth_routes(
                page,
                base_url=base_url,
                signed_headers=signed_headers,
                provider_subject=PROVIDER_SUBJECT,
                provider_email=PROVIDER_EMAIL,
                display_name=DISPLAY_NAME,
            )

        _login_for_proof(page, base_url=base_url, email=email, password=password)
        create_roster(page, roster_name=roster_name)
        create_template(page, template_name=template_name)
        open_class_workspace(page, roster_name=roster_name)

        open_grouping_workspace(page, template_name=template_name)
        _start_grouping_draft(page)
        open_seating_workspace(page, template_name=template_name)
        _start_seating_draft(page)

        for width, height in VIEWPORTS:
            _verify_viewport(
                page,
                width=width,
                height=height,
                roster_name=roster_name,
                template_name=template_name,
            )

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the share/export affordance browser proof."""

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
            email=config.email,
            password=config.password,
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
