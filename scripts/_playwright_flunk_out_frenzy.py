"""Shared Playwright helpers for Flunk-Out Frenzy route/browser proofs.

Entry-point scripts should import these helpers instead of duplicating route
login/bootstrap/runtime-start steps across multiple files.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

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
    """Log in through the protected Flunk-Out Frenzy route and wait for shell-ready."""

    for attempt in range(3):
        page.goto(f"{base_url}{APP_PATH}", wait_until="domcontentloaded")
        try:
            wait_for_shell_ready(page)
            expect(page).to_have_url(re.compile(re.escape(APP_PATH) + r"$"))
            return
        except AssertionError:
            login_dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
            if login_dialog.count() > 0:
                expect(login_dialog).to_be_visible()
                login_dialog.get_by_label("E-post").fill(email)
                login_dialog.get_by_label("Lösenord").fill(password)
                login_dialog.get_by_role(
                    "button", name=re.compile(r"Logga in", re.IGNORECASE)
                ).click()
                page.wait_for_timeout(1000)
            elif attempt == 0:
                page.goto(f"{base_url}/login", wait_until="domcontentloaded")
                login_page_dialog = page.get_by_role(
                    "dialog", name=re.compile(r"Logga in", re.IGNORECASE)
                )
                if login_page_dialog.count() > 0:
                    expect(login_page_dialog).to_be_visible()
                    login_page_dialog.get_by_label("E-post").fill(email)
                    login_page_dialog.get_by_label("Lösenord").fill(password)
                    login_page_dialog.get_by_role(
                        "button", name=re.compile(r"Logga in", re.IGNORECASE)
                    ).click()
                    page.wait_for_timeout(1000)
            if attempt == 2:
                raise
            page.wait_for_timeout(1000)


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
