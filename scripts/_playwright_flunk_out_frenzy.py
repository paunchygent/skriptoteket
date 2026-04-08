"""Shared Playwright helpers for Flunk-Out Frenzy route/browser proofs.

Entry-point scripts should import these helpers instead of duplicating route
login/bootstrap/runtime-start steps across multiple files.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from scripts._playwright_auth import login_via_auth_entry

APP_PATH = "/apps/games.flunk_out_frenzy"


def wait_for_shell_ready(page: Page) -> None:
    """Wait for either a bootstrap-ready shell or a visible bootstrap error."""

    ready_state = page.locator('[data-test="bootstrap-ready"]')
    error_state = page.locator('[data-test="bootstrap-error"]')

    for _ in range(60):
        if ready_state.count() > 0 and ready_state.first.is_visible():
            return
        if error_state.count() > 0 and error_state.first.is_visible():
            raise AssertionError(
                f"Flunk-Out Frenzy bootstrap failed: {error_state.first.inner_text()}"
            )
        page.wait_for_timeout(500)

    raise AssertionError("Flunk-Out Frenzy did not reach a bootstrap-ready state.")


def login_to_flunk_out_frenzy(page: Page, *, base_url: str, email: str, password: str) -> None:
    """Log in through `/auth/login` and wait for the Flunk-Out Frenzy shell."""

    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=APP_PATH,
        success_heading_pattern=r"Flunk-Out Frenzy",
    )
    wait_for_shell_ready(page)
    expect(page).to_have_url(re.compile(re.escape(APP_PATH) + r"$"))


def verify_runtime_start(page: Page) -> None:
    """Start the runtime and assert that renderer mount reaches ready state."""

    page.get_by_role("button", name=re.compile(r"^Start$", re.IGNORECASE)).click()
    runtime_host = page.locator('[data-test="runtime-host-placeholder"]')
    expect(runtime_host).to_have_attribute("data-runtime-load-state", "ready", timeout=30000)
    expect(runtime_host).to_have_attribute("data-runtime-mounted", "true", timeout=30000)
    expect(page.locator('[data-test="runtime-renderer-canvas"]')).to_be_visible()


def wait_for_debug_handle(page: Page, *, timeout_steps: int = 40, interval_ms: int = 250) -> None:
    """Wait for the DEV debug handle to be registered on window."""

    for _ in range(timeout_steps):
        if page.evaluate('typeof window.__FOF_DEBUG__ !== "undefined"'):
            return
        page.wait_for_timeout(interval_ms)
    raise AssertionError("window.__FOF_DEBUG__ was not available in DEV mode.")
