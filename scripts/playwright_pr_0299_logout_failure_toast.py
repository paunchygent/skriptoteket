"""Playwright proof for PR-0299 logout failure toast behavior.

Purpose:
    Exercise the live authenticated SPA shell through the local HuleEdu signed
    continuation harness and force the shared logout endpoint to time out. The
    proof verifies that the failure is displayed as a dismissible failure toast
    without inserting the old AuthLayout inline panel into the workspace.

Relationships:
    - Reuses the EPIC-28 local HuleEdu auth helpers for browser-session proof.
    - Complements the focused App/AuthLayout Vitest coverage for PR-0299.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import (
    DEFAULT_PROVIDER_SUBJECT,
    install_local_huleedu_auth_routes,
    new_private_key,
    public_key_pem,
    seed_huleedu_projection,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
    verify_profile_continuation_api,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0299-logout-failure-toast")
APP_PATH = "/apps/classroom.group-seating-studio"
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0299"
PROVIDER_EMAIL = "pr-0299-live-huleedu@example.test"
DISPLAY_NAME = "PR 0299 Teacher"
LOGOUT_FAILURE_MESSAGE = (
    "Det gick inte att logga ut just nu. Kontrollera din internetanslutning "
    "och klicka på Logga ut igen."
)


def _install_slow_logout_route(page: Page, *, base_url: str) -> None:
    """Force shared logout to exceed the frontend timeout contract."""

    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def slow_logout(route) -> None:  # type: ignore[no-untyped-def]
        time.sleep(11.25)
        try:
            route.fulfill(
                status=504,
                headers=cors_headers,
                body=json.dumps({"error": {"message": "simulated slow logout"}}),
            )
        except Exception:
            return

    page.route("https://api.hule.education/v1/auth/logout", slow_logout)


def _open_authenticated_planner(page: Page, *, base_url: str) -> None:
    """Open Klassrumskartan and wait for the authenticated shell."""

    page.goto(f"{base_url.rstrip('/')}{APP_PATH}", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"^Klassrumskartan$"))).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE))).to_be_visible()


def _assert_forced_logout_failure(page: Page) -> None:
    """Click logout and assert the timeout failure is a toast, not layout chrome."""

    heading = page.get_by_role("heading", name=re.compile(r"^Klassrumskartan$"))
    before_box = heading.bounding_box()
    if before_box is None:
        raise AssertionError("Klassrumskartan heading did not have a measurable box before logout.")

    page.get_by_role("button", name=re.compile(r"Logga ut", re.IGNORECASE)).click()
    toast = page.locator(".toast.toast-failure").filter(has_text=LOGOUT_FAILURE_MESSAGE)
    expect(toast).to_be_visible(timeout=15_000)
    expect(toast.get_by_role("button", name="Stäng")).to_be_visible()

    main_message = page.locator("main").get_by_text(LOGOUT_FAILURE_MESSAGE)
    if main_message.count() != 0:
        raise AssertionError(
            "Logout failure was rendered inside main layout instead of toast host."
        )

    after_box = heading.bounding_box()
    if after_box is None:
        raise AssertionError("Klassrumskartan heading disappeared after forced logout failure.")
    if abs(after_box["y"] - before_box["y"]) > 1:
        raise AssertionError(
            f"Workspace shifted vertically after logout failure: before={before_box['y']}, "
            f"after={after_box['y']}"
        )

    page.screenshot(path=str(ARTIFACTS_DIR / "logout-failure-toast.png"), full_page=True)


def main() -> None:
    """Run the PR-0299 authenticated browser proof."""

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    signing_key = new_private_key()
    local_user_id = seed_huleedu_projection(
        local_user_id=str(uuid4()),
        provider_subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
        role="contributor",
    )
    signed_headers = signed_identity_headers(
        private_key=signing_key,
        subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        display_name=DISPLAY_NAME,
        jti="playwright-pr-0299-logout-failure-toast",
    )

    with temporary_backend_server(
        public_key_pem(signing_key),
        artifacts_dir=ARTIFACTS_DIR,
        port=None,
    ) as backend_url:
        with temporary_vite_server(proxy_target=backend_url) as base_url:
            with sync_playwright() as playwright:
                verify_profile_continuation_api(
                    playwright,
                    backend_url=backend_url,
                    signed_headers=signed_headers,
                    local_user_id=local_user_id,
                )

                browser = launch_chromium(playwright)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                seen: list[str] = []
                install_local_huleedu_auth_routes(
                    page,
                    base_url=base_url,
                    signed_headers=signed_headers,
                    provider_subject=PROVIDER_SUBJECT,
                    provider_email=PROVIDER_EMAIL,
                    display_name=DISPLAY_NAME,
                    seen=seen,
                )
                _install_slow_logout_route(page, base_url=base_url)
                _open_authenticated_planner(page, base_url=base_url)
                _assert_forced_logout_failure(page)

                if "app-continuation-live" not in seen:
                    raise AssertionError("Authenticated proof did not hit live app continuation.")

                context.close()
                browser.close()

    print(
        "playwright-pr-0299-logout-failure-toast: ok "
        f"screenshot={ARTIFACTS_DIR / 'logout-failure-toast.png'}"
    )


if __name__ == "__main__":
    main()
