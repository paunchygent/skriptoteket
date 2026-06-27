"""Shared Playwright auth helpers for canonical browser proofs.

Purpose:
    Drive Skriptoteket proof scripts through the HuleEdu-owned browser-session
    ceremony without minting app-local cookies or calling protected APIs
    directly.

Relationships:
    - Opens Skriptoteket's `/auth/login` handoff route.
    - Follows the HuleEdu login UI and waits for the protected Skriptoteket
      destination that proves app continuation succeeded.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

AUTH_ENTRY_PATH = "/auth/login"
HULEEDU_LOGIN_API_PATH = "/v1/auth/login"
AUTH_HANDOFF_ACTION_PATTERN = re.compile(
    r"(logga in igen|öppna inloggningen|inloggningen|logga in)",
    re.IGNORECASE,
)


def _is_visible(locator: Locator) -> bool:
    return locator.count() > 0 and locator.first.is_visible()


def _handoff_link(page: Page) -> Locator:
    return page.get_by_role("link", name=AUTH_HANDOFF_ACTION_PATTERN).first


def _try_handoff_href(handoff_link: Locator) -> str | None:
    try:
        return handoff_link.get_attribute("href", timeout=1_000)
    except PlaywrightTimeoutError:
        return None


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
        if _is_visible(success_heading):
            return "success"
        if _is_visible(page.locator("#email")) and _is_visible(page.locator("#password")):
            return "huleedu_form"
        if _is_visible(auth_form):
            return "form"
        if _is_visible(_handoff_link(page)):
            return "handoff_link"
        page.wait_for_timeout(interval_ms)
        elapsed_ms += interval_ms

    raise AssertionError(
        "Neither the auth-entry form nor the expected post-login destination became visible."
    )


def _submit_huleedu_form(page: Page, *, email: str, password: str) -> None:
    """Submit the HuleEdu browser login form and assert the login API accepted it."""

    email_input = page.locator("#email")
    password_input = page.locator("#password")
    expect(email_input).to_be_visible(timeout=15_000)
    expect(password_input).to_be_visible(timeout=15_000)
    email_input.fill(email)
    password_input.fill(password)

    login_button = page.get_by_role("button", name=re.compile("logga in", re.I)).first
    expect(login_button).to_be_enabled(timeout=15_000)
    try:
        with page.expect_response(
            lambda response: HULEEDU_LOGIN_API_PATH in urlparse(response.url).path,
            timeout=10_000,
        ) as response_info:
            login_button.click()
    except PlaywrightTimeoutError:
        with page.expect_response(
            lambda response: HULEEDU_LOGIN_API_PATH in urlparse(response.url).path,
            timeout=10_000,
        ) as response_info:
            password_input.press("Enter")

    response = response_info.value
    if response.status == 200:
        return
    response_text = response.text()[:500].replace(email, "<email>").replace(password, "<password>")
    raise AssertionError(f"HuleEdu login API returned {response.status}: {response_text}")


def _submit_auth_surface(
    page: Page,
    *,
    auth_form: Locator,
    visible_surface: str,
    email: str,
    password: str,
) -> None:
    """Submit whichever supported browser-auth surface is currently visible."""

    if visible_surface == "huleedu_form":
        _submit_huleedu_form(page, email=email, password=password)
        return

    if visible_surface == "form":
        auth_form.get_by_label("E-post").fill(email)
        auth_form.get_by_label("Lösenord").fill(password)
        auth_form.get_by_role("button", name=re.compile(r"^Logga in$", re.IGNORECASE)).click()
        return

    raise AssertionError(f"Unsupported auth surface: {visible_surface}")


def _write_auth_failure_artifacts(
    *,
    page: Page,
    artifact_dir: Path | None,
    screenshot_name: str,
    reason: str,
) -> None:
    if artifact_dir is None:
        return
    state = {
        "reason": reason,
        "title": page.title(),
        "url": page.url,
    }
    (artifact_dir / "auth-failure-state.json").write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    page.screenshot(path=str(artifact_dir / screenshot_name), full_page=True)


def _follow_handoff_link(page: Page) -> None:
    """Navigate through the visible HuleEdu ceremony link from the auth handoff."""

    handoff_link = _handoff_link(page)
    href = _try_handoff_href(handoff_link)
    if href:
        try:
            page.goto(href, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            if "ERR_ABORTED" not in str(exc):
                raise
        return
    try:
        handoff_link.click(no_wait_after=True, timeout=1_000)
    except PlaywrightTimeoutError:
        return


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
        try:
            visible_surface = _wait_for_auth_form_or_success(
                page=page,
                auth_form=auth_form,
                success_heading=success_heading,
                timeout_ms=form_timeout_ms,
            )
        except AssertionError:
            _write_auth_failure_artifacts(
                page=page,
                artifact_dir=failure_artifacts_dir,
                screenshot_name=failure_screenshot_name,
                reason="auth_surface_timeout",
            )
            raise
        if visible_surface == "success":
            return
        if visible_surface == "handoff_link":
            _follow_handoff_link(page)
            visible_surface = _wait_for_auth_form_or_success(
                page=page,
                auth_form=auth_form,
                success_heading=success_heading,
                timeout_ms=form_timeout_ms,
            )
            if visible_surface == "success":
                return
            if visible_surface == "handoff_link":
                if failure_artifacts_dir is not None:
                    handoff_link = _handoff_link(page)
                    state = {
                        "url": page.url,
                        "handoff_href": _try_handoff_href(handoff_link),
                    }
                    (failure_artifacts_dir / "auth-handoff-state.json").write_text(
                        json.dumps(state, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    page.screenshot(
                        path=str(failure_artifacts_dir / failure_screenshot_name),
                        full_page=True,
                    )
                raise AssertionError("HuleEdu auth handoff link did not open a login form.")

        _submit_auth_surface(
            page,
            auth_form=auth_form,
            visible_surface=visible_surface,
            email=email,
            password=password,
        )

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
