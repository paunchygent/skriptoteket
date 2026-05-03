"""Playwright proof for PR-0287 Smart settings panel persistence.

Purpose:
    Exercise the live Klassrumskartan grouping and seating Smart settings
    surfaces through the local authenticated app-continuation lane. The proof
    verifies that internal settings interactions keep the panel open while
    Escape, backdrop click, and intentional Rules navigation still close it.

Relationships:
    - Reuses the shared Klassrumskartan Playwright helpers for auth, class,
      room, and workspace setup.
    - Complements the focused Vue specs for the PR-0287 watcher refactor.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Page, expect, sync_playwright

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

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0287-smart-settings-persistence")
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0287"
PROVIDER_EMAIL = "pr-0287-live-huleedu@example.test"
DISPLAY_NAME = "PR 0287 Teacher"


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
    """Create a simple grouping draft before exercising settings."""

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
    """Create a simple seating draft before exercising settings."""

    with page.expect_response(re.compile(r".*/drafts/seating/new$")) as response_info:
        page.locator('[data-test="new-seating-draft"]').click()
    if not response_info.value.ok:
        raise AssertionError(
            f"Expected seating draft creation to succeed, got {response_info.value.status}"
        )
    expect(page.locator('[data-test="seating-open-settings"]')).to_be_visible()


def _verify_grouping_settings(page: Page) -> None:
    """Verify grouping Smart settings stay open for internal interactions."""

    page.locator('[data-test="grouping-open-settings"]').click()
    drawer = page.locator('[data-test="grouping-settings-drawer"]')
    expect(drawer).to_be_visible()
    expect(drawer).to_have_attribute("role", "dialog")

    page.locator('[data-test="grouping-settings-history-toggle"]').click()
    expect(drawer).to_be_visible()
    page.locator('[data-test="grouping-settings-seating-toggle"]').click()
    expect(drawer).to_be_visible()

    page.screenshot(
        path=str(ARTIFACTS_DIR / "grouping-settings-after-internal-toggle.png"),
        full_page=True,
    )

    page.keyboard.press("Escape")
    expect(drawer).not_to_be_visible()

    page.locator('[data-test="grouping-open-settings"]').click()
    expect(drawer).to_be_visible()
    page.locator('[data-test="grouping-settings-open-rules"]').click()
    expect(drawer).not_to_be_visible()
    expect(page.locator('[data-test="rules-workspace-layout"]')).to_be_visible()


def _verify_seating_settings(page: Page) -> None:
    """Verify seating Smart settings stay open for internal interactions."""

    page.locator('[data-test="seating-open-settings"]').click()
    drawer = page.locator('[data-test="seating-settings-drawer"]')
    expect(drawer).to_be_visible()
    expect(drawer).to_have_attribute("role", "dialog")

    page.locator('[data-test="seating-settings-history-toggle"]').click()
    expect(drawer).to_be_visible()

    page.screenshot(
        path=str(ARTIFACTS_DIR / "seating-settings-after-history-toggle.png"),
        full_page=True,
    )

    page.locator('[data-test="seating-settings-backdrop"]').click(position={"x": 8, "y": 8})
    expect(drawer).not_to_be_visible()

    page.locator('[data-test="seating-open-settings"]').click()
    expect(drawer).to_be_visible()
    page.keyboard.press("Escape")
    expect(drawer).not_to_be_visible()


def _run(
    *,
    base_url: str,
    backend_base_url: str,
    private_key: RSAPrivateKey,
    email: str,
    password: str,
) -> None:
    """Run the live Smart settings persistence proof against one stack."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_suffix = str(int(time.time()))
    roster_name = f"PR0287 Klass {run_suffix}"
    template_name = f"PR0287 Sal {run_suffix}"
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
        jti=f"pr-0287-smart-settings-{run_suffix}",
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
        _verify_grouping_settings(page)

        focus_workspace_mode(page, label="Sittplatser")
        open_seating_workspace(page, template_name=template_name)
        _start_seating_draft(page)
        _verify_seating_settings(page)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {ARTIFACTS_DIR}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse proof options and run the Smart settings persistence proof."""

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
