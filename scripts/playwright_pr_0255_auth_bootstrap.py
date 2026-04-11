"""PR-0255 live Playwright proof for HuleEdu session plus app continuation.

Purpose:
    Verify that the SPA can bootstrap from a HuleEdu shared browser session,
    then hydrate Skriptoteket-local identity from the real continuation route.

Relationships:
    - Targets PR-0255 / REV-PR-0251 remediation evidence.
    - Seeds a HuleEdu-linked local projection in the real database.
    - Sends signed gateway identity headers to the real backend route through
      the same `/api` path the SPA uses behind the Vite proxy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

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

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0255-auth-bootstrap")
PROVIDER_SUBJECT = DEFAULT_PROVIDER_SUBJECT


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
    seen: list[str],
) -> None:
    """Mock HuleEdu auth while app continuation continues to the real backend."""
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route) -> None:
        seen.append("huleedu-session")
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
                    "policy": {
                        "roles": ["teacher", "external-admin"],
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


def _assert_bootstrap(page: Page, *, base_url: str, seen: list[str]) -> None:
    """Assert local continuation, not provider roles, controls contributor access."""
    page.goto(f"{base_url}/editor", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=15_000)
    expect(page.get_by_role("link", name="Mina verktyg").first).to_be_visible()
    expect(page.get_by_role("link", name="Alla verktyg")).to_have_count(0)
    if page.url != f"{base_url}/editor":
        raise AssertionError(f"Expected to remain on /editor, got {page.url}")
    required = {"huleedu-session", "app-continuation-live", "huleedu-csrf", "my-tools"}
    missing = required.difference(seen)
    if missing:
        raise AssertionError(f"Missing expected bootstrap calls: {sorted(missing)}; seen={seen}")


def _run(base_url: str, *, backend_url: str, private_key: RSAPrivateKey) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    seen: list[str] = []
    local_user_id = seed_huleedu_projection(
        email="pr-0255-live-huleedu@example.test",
        display_name="Local Teacher",
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        jti="pr-0255-live-context",
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
        page = context.new_page()
        _install_auth_routes(
            page,
            base_url=base_url,
            signed_headers=signed_headers,
            seen=seen,
        )
        _assert_bootstrap(page, base_url=base_url, seen=seen)
        page.screenshot(path=str(ARTIFACTS_DIR / "editor-local-continuation.png"), full_page=True)
        context.close()
        browser.close()
    print(
        "playwright-pr-0255-auth-bootstrap: ok "
        "real backend route valid=200 missing=401; "
        "HuleEdu subject stayed provider metadata; local contributor projection opened /editor"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0255 HuleEdu/app-continuation proof")
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
