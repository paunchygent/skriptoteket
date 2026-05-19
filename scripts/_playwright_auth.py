"""Shared Playwright auth helpers for canonical browser proofs.

This module keeps the repo's Playwright login flows aligned with the shipped
page-based `/auth/login` contract so canonical smoke entrypoints do not hardcode
stale modal-era selectors or legacy `/login` routes.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Locator, Page, expect

AUTH_ENTRY_PATH = "/auth/login"


def _wait_for_auth_form_or_success(
    *,
    page: Page,
    auth_form: Locator,
    success_heading: Locator,
    timeout_ms: int,
) -> str:
    """Wait until either the auth form or the post-login heading becomes visible."""

    elapsed_ms = 0
    interval_ms = 250
    while elapsed_ms <= timeout_ms:
        if success_heading.count() > 0 and success_heading.first.is_visible():
            return "success"
        if auth_form.count() > 0 and auth_form.first.is_visible():
            return "form"
        page.wait_for_timeout(interval_ms)
        elapsed_ms += interval_ms

    raise AssertionError(
        "Neither the auth-entry form nor the expected post-login destination became visible."
    )


def login_via_auth_entry(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    next_path: str,
    success_heading_pattern: str,
    attempts: int = 3,
    failure_artifacts_dir: Path | None = None,
    failure_screenshot_name: str = "login-failure.png",
    form_timeout_ms: int = 15_000,
    success_timeout_ms: int = 30_000,
) -> None:
    """Log in through `/auth/login` and wait for one authenticated destination."""

    auth_entry_url = f"{base_url}{AUTH_ENTRY_PATH}?next={quote(next_path, safe='/?=&:#')}"
    success_heading = page.get_by_role(
        "heading", name=re.compile(success_heading_pattern, re.IGNORECASE)
    )

    for attempt in range(attempts):
        page.goto(auth_entry_url, wait_until="domcontentloaded")
        auth_form = page.locator("form").first
        visible_surface = _wait_for_auth_form_or_success(
            page=page,
            auth_form=auth_form,
            success_heading=success_heading,
            timeout_ms=form_timeout_ms,
        )
        if visible_surface == "success":
            return

        auth_form.get_by_label("E-post").fill(email)
        auth_form.get_by_label("Lösenord").fill(password)
        auth_form.get_by_role("button", name=re.compile(r"^Logga in$", re.IGNORECASE)).click()

        try:
            expect(success_heading).to_be_visible(timeout=success_timeout_ms)
            return
        except AssertionError:
            if attempt == attempts - 1 and failure_artifacts_dir is not None:
                page.screenshot(
                    path=str(failure_artifacts_dir / failure_screenshot_name),
                    full_page=True,
                )
            if attempt == attempts - 1:
                raise
            page.wait_for_timeout(1_000)

    raise AssertionError("Auth-entry login did not reach the expected destination.")


def login_to_browse(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    failure_artifacts_dir: Path | None = None,
) -> None:
    """Log in through the protected browse route and wait for the catalog shell."""

    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path="/browse",
        success_heading_pattern=r"^Katalog$",
        failure_artifacts_dir=failure_artifacts_dir,
        failure_screenshot_name="login-failure.png",
    )
