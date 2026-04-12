"""PR-0253 live proof for local browser-auth retirement.

Purpose:
    Exercise the hard-break auth contract with real backend routes: signed
    HuleEdu Gateway context authorizes app reads/writes, missing context fails
    closed even with stale CSRF, missing projection fails closed, and the SPA
    login entry hands off to the shared inloggning instead of rendering a
    local form.

Relationships:
    - Uses shared HuleEdu signing/projection helpers from
      `scripts._playwright_huleedu_auth`.
    - Complements static no-zombie contract tests for removed local auth paths.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Page, Playwright, Route, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import (
    DEFAULT_PROVIDER_SUBJECT,
    backend_url_for_spa,
    new_private_key,
    public_key_pem,
    seed_huleedu_projection,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0253-auth-retirement")
PROVIDER_SUBJECT = DEFAULT_PROVIDER_SUBJECT
MISSING_PROJECTION_SUBJECT = "missing-pr-0253-projection"
INTERNAL_IDENTITY_HEADER_PREFIX = "x-huledu-identity-"


def _fulfill_json(route: Route, payload: dict[str, object], *, status: int = 200) -> None:
    route.fulfill(
        status=status,
        headers={"content-type": "application/json"},
        body=json.dumps(payload),
    )


def _assert_browser_did_not_set_internal_identity_headers(route: Route) -> None:
    browser_headers = sorted(
        header_name
        for header_name in route.request.headers
        if header_name.lower().startswith(INTERNAL_IDENTITY_HEADER_PREFIX)
    )
    if browser_headers:
        raise AssertionError(
            f"Browser request set internal HuleEdu identity headers: {', '.join(browser_headers)}"
        )


def _install_browser_gateway_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    provider_subject: str,
    provider_email: str,
    seen: list[str],
) -> None:
    """Mock HuleEdu browser auth and inject signed app context at the edge."""
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route: Route) -> None:
        seen.append("huleedu-session")
        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps(
                {
                    "authenticated": True,
                    "user": {
                        "user_id": provider_subject,
                        "email": provider_email,
                        "email_verified": True,
                    },
                    "profile": {"display_name": "Provider Teacher", "locale": "sv-SE"},
                    "policy": {
                        "roles": ["teacher"],
                        "grants": ["tools:run"],
                        "feature_flags": ["inline-completion"],
                    },
                    "session": {
                        "transport": "cookie",
                        "csrf_required": True,
                        "expires_at": "2026-04-11T12:30:00Z",
                    },
                }
            ),
        )

    def huleedu_csrf(route: Route) -> None:
        seen.append("huleedu-csrf")
        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps({"csrf_token": "csrf-token"}),
        )

    def app_continuation(route: Route) -> None:
        seen.append("app-continuation-live")
        _assert_browser_did_not_set_internal_identity_headers(route)
        route.continue_(headers={**route.request.headers, **signed_headers})

    def my_tools(route: Route) -> None:
        seen.append("my-tools")
        _fulfill_json(route, {"tools": []})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/profile/app-continuation", app_continuation)
    page.route("**/api/v1/my-tools", my_tools)


def _verify_api_contract(
    playwright: Playwright,
    *,
    app_api_base_url: str,
    private_key: RSAPrivateKey,
    local_user_id: UUID,
) -> None:
    """Exercise signed read/write and fail-closed cases through the app API edge."""
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=DEFAULT_PROVIDER_SUBJECT,
        jti="pr-0253-valid-context",
    )
    missing_projection_headers = signed_identity_headers(
        private_key=private_key,
        subject="missing-pr-0253-projection",
        jti="pr-0253-missing-projection-context",
    )

    request_context = playwright.request.new_context(base_url=app_api_base_url)
    try:
        direct_missing = request_context.patch(
            "/api/v1/profile",
            headers={"X-CSRF-Token": "stale-local-token"},
            data={"display_name": "Should not save"},
        )
        if direct_missing.status != 401:
            raise AssertionError(
                f"Expected stale-CSRF/missing-context write to return 401, got "
                f"{direct_missing.status}"
            )

        read = request_context.get("/api/v1/profile", headers=signed_headers)
        if read.status != 200:
            raise AssertionError(f"Expected signed profile read 200, got {read.status}")
        if read.json()["user"]["id"] != str(local_user_id):
            raise AssertionError("Signed profile read returned the wrong local projection.")

        write = request_context.patch(
            "/api/v1/profile",
            headers=signed_headers,
            data={"display_name": "PR-0253 Signed Write"},
        )
        if write.status != 200:
            raise AssertionError(f"Expected signed profile write 200, got {write.status}")
        if write.json()["profile"]["display_name"] != "PR-0253 Signed Write":
            raise AssertionError("Signed profile write did not persist through the app API.")

        missing_projection = request_context.get(
            "/api/v1/profile",
            headers=missing_projection_headers,
        )
        if missing_projection.status != 401:
            raise AssertionError(
                f"Expected missing projection to return 401, got {missing_projection.status}"
            )
    finally:
        request_context.dispose()


def _verify_frontend_ceremony(playwright: Playwright, *, base_url: str) -> None:
    """Verify `/auth/login` is an inloggning handoff surface, not a local form."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    browser = launch_chromium(playwright)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        page.goto(f"{base_url}/auth/login?next=/editor", wait_until="domcontentloaded")
        login_link = page.get_by_role("link", name="Fortsätt till inloggning")
        expect(login_link).to_be_visible(timeout=10_000)
        if page.locator("form").count() != 0:
            raise AssertionError("Auth login entry rendered a local form.")
        href = login_link.get_attribute("href")
        if href is None or not href.startswith("https://api.hule.education/auth/login"):
            raise AssertionError(f"Expected browser auth ceremony href, got {href!r}")
        if "/v1/auth/login" in href:
            raise AssertionError(f"Auth ceremony link must not target the login API, got {href!r}")
        if "next=" not in href:
            raise AssertionError(f"Expected preserved next target in handoff href, got {href!r}")
        page.screenshot(path=str(ARTIFACTS_DIR / "inloggning-handoff.png"), full_page=True)
    finally:
        context.close()
        browser.close()


def _verify_browser_gateway_success(
    playwright: Playwright,
    *,
    base_url: str,
    private_key: RSAPrivateKey,
) -> None:
    """Prove protected browser routes work only through gateway-injected context."""
    seen: list[str] = []
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        jti="pr-0253-browser-valid-context",
    )
    browser = launch_chromium(playwright)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        _install_browser_gateway_routes(
            page,
            base_url=base_url,
            signed_headers=signed_headers,
            provider_subject=PROVIDER_SUBJECT,
            provider_email="pr-0253-live-huleedu@example.test",
            seen=seen,
        )
        page.goto(f"{base_url}/editor?pick=1", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=15_000)
        expect(page.get_by_test_id("editor-hub-my-tools-empty")).to_be_visible(timeout=15_000)
        if page.url != f"{base_url}/editor?pick=1":
            raise AssertionError(f"Expected browser to remain on protected /editor, got {page.url}")
        required = {"huleedu-session", "app-continuation-live", "huleedu-csrf", "my-tools"}
        missing = required.difference(seen)
        if missing:
            raise AssertionError(
                f"Missing expected browser gateway calls: {sorted(missing)}; seen={seen}"
            )
        page.screenshot(path=str(ARTIFACTS_DIR / "browser-gateway-editor.png"), full_page=True)
    finally:
        context.close()
        browser.close()


def _verify_browser_gateway_missing_projection(
    playwright: Playwright,
    *,
    base_url: str,
    private_key: RSAPrivateKey,
) -> None:
    """Prove authenticated HuleEdu users without projection reach deliberate UX."""
    seen: list[str] = []
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=MISSING_PROJECTION_SUBJECT,
        jti="pr-0253-browser-missing-projection-context",
    )
    browser = launch_chromium(playwright)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        _install_browser_gateway_routes(
            page,
            base_url=base_url,
            signed_headers=signed_headers,
            provider_subject=MISSING_PROJECTION_SUBJECT,
            provider_email="missing-pr-0253-projection@example.test",
            seen=seen,
        )
        page.goto(f"{base_url}/editor?pick=1", wait_until="domcontentloaded")
        expect(page).to_have_url(
            re.compile(f"^{re.escape(base_url)}/auth/provisioning-required"),
            timeout=15_000,
        )
        expect(page.get_by_role("heading", name="Åtkomsten behöver aktiveras")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("Du är inloggad")).to_be_visible()
        required = {"huleedu-session", "app-continuation-live"}
        missing = required.difference(seen)
        if missing:
            raise AssertionError(
                f"Missing expected missing-projection gateway calls: {sorted(missing)}; seen={seen}"
            )
        if "my-tools" in seen:
            raise AssertionError("Missing-projection branch reached protected my-tools loading.")
        page.screenshot(path=str(ARTIFACTS_DIR / "browser-missing-projection.png"), full_page=True)
    finally:
        context.close()
        browser.close()


def _run(base_url: str, *, app_api_base_url: str, private_key: RSAPrivateKey) -> None:
    local_user_id = seed_huleedu_projection(
        email="pr-0253-live-huleedu@example.test",
        display_name="PR-0253 Teacher",
    )
    with sync_playwright() as playwright:
        _verify_api_contract(
            playwright,
            app_api_base_url=app_api_base_url,
            private_key=private_key,
            local_user_id=local_user_id,
        )
        _verify_frontend_ceremony(playwright, base_url=base_url)
        _verify_browser_gateway_success(
            playwright,
            base_url=base_url,
            private_key=private_key,
        )
        _verify_browser_gateway_missing_projection(
            playwright,
            base_url=base_url,
            private_key=private_key,
        )
    print(
        "playwright-pr-0253-auth-retirement: ok "
        "signed read/write=200; stale-CSRF missing-context=401; "
        "missing projection=401; /auth/login hands off to inloggning; "
        "browser gateway-injected app context opens /editor and missing projection "
        "lands on provisioning-required"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0253 auth-retirement proof")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Running SPA base URL; ignored when --start-vite is set.",
    )
    parser.add_argument(
        "--start-vite",
        action="store_true",
        help="Start a temporary Vite dev server for this proof.",
    )
    parser.add_argument(
        "--start-backend",
        action="store_true",
        help="Start the real repo dev backend on 127.0.0.1:8000 with the verifier key.",
    )
    args = parser.parse_args()

    private_key = new_private_key()
    public_key = public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"Invalid --base-url: {base_url}")
        app_api_base_url = base_url.rstrip("/") if args.start_vite else backend_url.rstrip("/")
        _run(
            base_url.rstrip("/"),
            app_api_base_url=app_api_base_url,
            private_key=private_key,
        )

    if args.start_backend:
        with temporary_backend_server(public_key, artifacts_dir=ARTIFACTS_DIR) as backend_url:
            if args.start_vite:
                with temporary_vite_server() as base_url:
                    run_with_base_url(base_url, backend_url)
                return
            run_with_base_url(args.base_url, backend_url)
        return

    if args.start_vite:
        with temporary_vite_server() as base_url:
            run_with_base_url(base_url, backend_url_for_spa(base_url))
        return

    run_with_base_url(args.base_url, backend_url_for_spa(args.base_url))


if __name__ == "__main__":
    main()
