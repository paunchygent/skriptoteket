"""PR-0256 live proof for the HuleEdu product-realm login ceremony.

Purpose:
    Verify that Skriptoteket sends signed-out users to the provider-approved
    HuleEdu `GET /auth/login` ceremony with app, realm, callback, and safe
    route continuation parameters, then resumes from `/auth/callback` after
    HuleEdu session bootstrap and signed app continuation.

Relationships:
    - Uses shared HuleEdu signing/projection helpers from
      `scripts._playwright_huleedu_auth`.
    - Complements focused Vitest coverage for the SPA auth URL helper and
      route guard callback behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import Page, expect, sync_playwright

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
    verify_profile_continuation_api,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0256-auth-ceremony")
PROVIDER_SUBJECT = DEFAULT_PROVIDER_SUBJECT
DEFAULT_REALM = "skriptoteket_standalone"
PROOF_NEXT_PATH = "/editor?draft=head#debug"


def _fulfill_json(route, payload: dict[str, object], *, status: int = 200) -> None:
    route.fulfill(
        status=status,
        headers={"content-type": "application/json"},
        body=json.dumps(payload),
    )


def _install_auth_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    authenticated: bool,
    seen: list[str],
) -> None:
    """Mock HuleEdu browser auth while app continuation hits the backend."""
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route) -> None:
        seen.append("huleedu-session")
        if not authenticated:
            route.fulfill(
                status=200,
                headers=cors_headers,
                body=json.dumps(
                    {
                        "authenticated": False,
                        "user": None,
                        "profile": None,
                        "policy": {
                            "roles": [],
                            "grants": [],
                            "feature_flags": [],
                        },
                        "session": {
                            "transport": "cookie",
                            "csrf_required": True,
                            "expires_at": None,
                        },
                    }
                ),
            )
            return

        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps(
                {
                    "authenticated": True,
                    "user": {
                        "user_id": PROVIDER_SUBJECT,
                        "email": "teacher@example.test",
                        "email_verified": True,
                    },
                    "profile": {"display_name": "Provider Teacher", "locale": "sv-SE"},
                    "context": {
                        "active_app": "skriptoteket",
                        "active_product_identity_realm": DEFAULT_REALM,
                        "realm_subject_id": PROVIDER_SUBJECT,
                    },
                    "policy": {
                        "roles": ["teacher"],
                        "grants": ["tools:run"],
                        "feature_flags": ["inline-completion"],
                    },
                    "session": {
                        "transport": "cookie",
                        "csrf_required": True,
                        "expires_at": "2026-04-12T12:30:00Z",
                    },
                }
            ),
        )

    def huleedu_csrf(route) -> None:
        seen.append("huleedu-csrf")
        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps({"csrf_token": "csrf-token"}),
        )

    def app_continuation(route) -> None:
        seen.append("app-continuation-live")
        route.continue_(headers={**route.request.headers, **signed_headers})

    def my_tools(route) -> None:
        seen.append("my-tools")
        _fulfill_json(route, {"tools": []})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/profile/app-continuation", app_continuation)
    page.route("**/api/v1/my-tools", my_tools)


def _assert_ceremony_link(page: Page, *, base_url: str) -> None:
    """Assert `/auth/login` points at the approved browser ceremony contract."""
    page.goto(
        f"{base_url}/auth/login?next={quote(PROOF_NEXT_PATH, safe='')}",
        wait_until="domcontentloaded",
    )
    login_link = page.get_by_role("link", name="Fortsätt till inloggning")
    expect(login_link).to_be_visible(timeout=10_000)
    if page.locator("form").count() != 0:
        raise AssertionError("Auth login entry rendered a local form.")

    href = login_link.get_attribute("href")
    if href is None:
        raise AssertionError("Auth login entry did not render a ceremony href.")
    if "/v1/auth/login" in href:
        raise AssertionError(f"Auth ceremony link must not target the login API, got {href!r}")

    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if f"{parsed.scheme}://{parsed.netloc}{parsed.path}" != (
        "https://api.hule.education/auth/login"
    ):
        raise AssertionError(f"Expected HuleEdu browser ceremony href, got {href!r}")
    expected_query = {
        "app": ["skriptoteket"],
        "product_identity_realm": [DEFAULT_REALM],
        "return_to": [f"{base_url}/auth/callback"],
        "next": [PROOF_NEXT_PATH],
    }
    for key, expected_value in expected_query.items():
        if query.get(key) != expected_value:
            raise AssertionError(
                f"Expected ceremony query {key}={expected_value}, got {query.get(key)} in {href!r}"
            )


def _assert_callback_bootstrap(page: Page, *, base_url: str, seen: list[str]) -> None:
    """Assert HuleEdu callback route resumes the intended protected route."""
    page.goto(
        f"{base_url}/auth/callback?next={quote(PROOF_NEXT_PATH, safe='')}",
        wait_until="domcontentloaded",
    )
    expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=15_000)
    if page.url != f"{base_url}{PROOF_NEXT_PATH}":
        raise AssertionError(f"Expected callback to resume {PROOF_NEXT_PATH}, got {page.url}")
    required = {"huleedu-session", "app-continuation-live", "huleedu-csrf", "my-tools"}
    missing = required.difference(seen)
    if missing:
        raise AssertionError(f"Missing expected auth bootstrap calls: {sorted(missing)}")


def _run(base_url: str, *, backend_url: str, private_key: RSAPrivateKey) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    seen: list[str] = []
    local_user_id = seed_huleedu_projection(
        email="pr-0256-live-huleedu@example.test",
        display_name="Local Product Teacher",
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        jti="pr-0256-realm-context",
    )

    with sync_playwright() as playwright:
        verify_profile_continuation_api(
            playwright,
            backend_url=backend_url,
            signed_headers=signed_headers,
            local_user_id=local_user_id,
        )
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        login_page = context.new_page()
        _install_auth_routes(
            login_page,
            base_url=base_url,
            signed_headers=signed_headers,
            authenticated=False,
            seen=seen,
        )
        _assert_ceremony_link(login_page, base_url=base_url)
        login_page.screenshot(path=str(ARTIFACTS_DIR / "ceremony-link.png"), full_page=True)
        login_page.close()

        callback_seen: list[str] = []
        callback_page = context.new_page()
        _install_auth_routes(
            callback_page,
            base_url=base_url,
            signed_headers=signed_headers,
            authenticated=True,
            seen=callback_seen,
        )
        _assert_callback_bootstrap(callback_page, base_url=base_url, seen=callback_seen)
        callback_page.screenshot(
            path=str(ARTIFACTS_DIR / "callback-resumed-editor.png"),
            full_page=True,
        )
        context.close()
        browser.close()

    print(
        "playwright-pr-0256-auth-ceremony: ok "
        "ceremony href app=skriptoteket realm=skriptoteket_standalone "
        f"return_to=/auth/callback next={PROOF_NEXT_PATH}; callback resumed {PROOF_NEXT_PATH}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0256 HuleEdu auth ceremony proof")
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
        _run(base_url.rstrip("/"), backend_url=backend_url, private_key=private_key)

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
