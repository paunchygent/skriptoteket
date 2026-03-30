"""Live auth-recovery proof for PR-0176.

Purpose:
    Verify the forgot-password resend affordance and the login-modal
    EMAIL_NOT_VERIFIED resend affordance against a running local SPA/backend.

Relationships:
    - Uses `scripts._playwright_config.get_config()` for base URL/env handling.
    - Writes screenshots to `.artifacts/pr-0176-auth-recovery-check/`.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import (
    APIRequestContext,
    Browser,
    Playwright,
    Response,
    expect,
    sync_playwright,
)
from playwright.sync_api import Error as PlaywrightError

from scripts._playwright_config import get_config

REGISTER_PASSWORD = "Hemligt123!"


def _find_chromium_headless_shell() -> str | None:
    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None

    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        for subdir in (
            "chrome-headless-shell-mac-arm64",
            "chrome-headless-shell-mac-x64",
        ):
            binary = candidate / subdir / "chrome-headless-shell"
            if binary.is_file():
                return str(binary)

    return None


def _launch_chromium(playwright: Playwright) -> Browser:
    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as exc:
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        message = str(exc)
        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)


def _register_unverified_user(request: APIRequestContext, *, base_url: str) -> tuple[str, str]:
    suffix = int(time.time())
    email = f"pr0176-auth-recovery-{suffix}@mail.harryda.se"

    response = request.post(
        f"{base_url}/api/v1/auth/register",
        data={
            "email": email,
            "password": REGISTER_PASSWORD,
            "first_name": "PR0176",
            "last_name": "Recovery",
        },
    )
    assert response.status == 201, (
        "Expected registration setup to create an unverified user for the auth-recovery proof. "
        f"Got {response.status}: {response.text()}"
    )
    return email, REGISTER_PASSWORD


def _assert_ok(response: Response, *, context: str) -> None:
    assert response.ok, f"{context} failed with {response.status}: {response.text()}"


def _derive_api_base_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    if parts.hostname not in {"127.0.0.1", "localhost"} or parts.port != 5173:
        return base_url

    netloc = f"{parts.hostname}:8000"
    return urlunsplit((parts.scheme, netloc, "", "", ""))


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _derive_api_base_url(base_url)

    artifacts_dir = Path(".artifacts/pr-0176-auth-recovery-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        email, password = _register_unverified_user(context.request, base_url=api_base_url)

        page.goto(f"{base_url}/forgot-password", wait_until="domcontentloaded")
        page.get_by_label("E-post").fill(email)
        with page.expect_response(
            lambda response: response.url.endswith("/api/v1/auth/forgot-password")
        ) as forgot_response_info:
            page.get_by_role("button", name="Skicka återställningslänk").click()
        _assert_ok(forgot_response_info.value, context="Forgot-password request")
        expect(
            page.get_by_text("Om kontot kan återställas skickas en återställningslänk.", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("heading", name="Inte verifierat än?")).to_be_visible()

        with page.expect_response(
            lambda response: response.url.endswith("/api/v1/auth/resend-verification")
        ) as forgot_resend_info:
            page.get_by_role("button", name="Skicka nytt verifieringsmejl").click()
        _assert_ok(forgot_resend_info.value, context="Forgot-password resend verification")
        expect(
            page.get_by_text("Om kontot finns skickas ett nytt verifieringsmail", exact=True)
        ).to_be_visible()
        page.screenshot(
            path=str(artifacts_dir / "forgot-password-resend.png"),
            full_page=True,
        )

        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
        expect(dialog).to_be_visible()
        dialog.get_by_label("E-post").fill(email)
        dialog.get_by_label("Lösenord").fill(password)
        with page.expect_response(
            lambda response: response.url.endswith("/api/v1/auth/login")
        ) as login_info:
            dialog.get_by_role("button", name=re.compile(r"^Logga in", re.IGNORECASE)).click()
        login_payload = login_info.value.json()
        assert login_info.value.status == 401, (
            "Expected unverified-user login to normalize to HTTP 401, "
            f"got {login_info.value.status}: {login_info.value.text()}"
        )
        assert login_payload.get("error", {}).get("code") == "EMAIL_NOT_VERIFIED", (
            "Expected unverified-user login to surface EMAIL_NOT_VERIFIED, "
            f"got {login_info.value.status}: {login_info.value.text()}"
        )
        expect(
            dialog.get_by_text("Verifiera din e-postadress innan du loggar in", exact=True)
        ).to_be_visible()

        resend_button = dialog.get_by_role("button", name="Skicka nytt verifieringsmejl")
        with page.expect_response(
            lambda response: response.url.endswith("/api/v1/auth/resend-verification")
        ) as login_resend_info:
            resend_button.click()
        _assert_ok(login_resend_info.value, context="Login-modal resend verification")
        expect(
            dialog.get_by_text("Om kontot finns skickas ett nytt verifieringsmail", exact=True)
        ).to_be_visible()
        expect(resend_button).to_be_enabled()
        page.screenshot(
            path=str(artifacts_dir / "login-modal-email-not-verified.png"),
            full_page=True,
        )

        context.close()
        browser.close()

    print(f"auth-recovery-live-check: ok ({artifacts_dir})")


if __name__ == "__main__":
    main()
