"""PR-0252 live Playwright proof for auth return-to-origin behavior.

Purpose:
    Verify that protected-route interruption, invalid-session recovery, and
    HuleEdu-authenticated returns all preserve the `/auth/login?next=...`
    contract while app continuation still hits the real backend route.

Relationships:
    - Targets `PR-0252` / `ST-28-02` under the EPIC-28 HuleEdu-owned session
      model.
    - Reuses shared HuleEdu signed-context helpers from
      `scripts._playwright_huleedu_auth`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0252-auth-return-to-origin")
PROTECTED_ROUTE = "/editor"


type BrowserAuthMode = str


def _fulfill_json(
    route,
    payload: dict[str, object],
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> None:
    route.fulfill(
        status=status,
        headers={"content-type": "application/json", **(headers or {})},
        body=json.dumps(payload),
    )


def _install_auth_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    state: dict[str, BrowserAuthMode | int],
    seen: list[str],
) -> None:
    """Mock HuleEdu browser session while continuation reaches the backend."""
    cors_headers = {
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route) -> None:
        seen.append(f"huleedu-session:{state['session']}")
        if state["session"] == "anonymous":
            _fulfill_json(
                route,
                {"error": {"code": "UNAUTHORIZED", "message": "No shared session"}},
                status=401,
                headers=cors_headers,
            )
            return

        _fulfill_json(
            route,
            {
                "authenticated": True,
                "user": {
                    "user_id": DEFAULT_PROVIDER_SUBJECT,
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
            },
            headers=cors_headers,
        )

    def huleedu_csrf(route) -> None:
        seen.append("huleedu-csrf")
        _fulfill_json(route, {"csrf_token": "csrf-token"}, headers=cors_headers)

    def app_continuation(route) -> None:
        seen.append("app-continuation-live")
        route.continue_(headers={**route.request.headers, **signed_headers})

    def my_tools(route) -> None:
        status = int(state["my_tools_status"])
        seen.append(f"my-tools:{status}")
        if status == 401:
            _fulfill_json(
                route,
                {"error": {"code": "UNAUTHORIZED", "message": "Session revoked"}},
                status=401,
            )
            return
        _fulfill_json(route, {"tools": []})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/profile/app-continuation", app_continuation)
    page.route("**/api/v1/my-tools", my_tools)


def _expect_auth_login_next(page: Page, *, base_url: str, next_path: str) -> None:
    """Assert the current page is the dedicated auth-entry route with next."""
    expected_prefix = f"{base_url}/auth/login"
    page.wait_for_url(lambda url: str(url).startswith(expected_prefix), timeout=15_000)
    parsed = urlparse(page.url)
    query = parse_qs(parsed.query)

    if parsed.path != "/auth/login":
        raise AssertionError(f"Expected /auth/login, got {parsed.path}")
    if query.get("next") != [next_path]:
        raise AssertionError(f"Expected next={next_path!r}, got {query.get('next')!r}")

    expect(page.get_by_role("heading", name="Logga in")).to_be_visible()


def _expect_editor(page: Page, *, base_url: str) -> None:
    """Assert the protected editor route is open after auth return."""
    page.wait_for_url(f"{base_url}{PROTECTED_ROUTE}", timeout=15_000)
    expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=15_000)
    expect(page.get_by_test_id("editor-hub-my-tools-empty")).to_be_visible(timeout=15_000)


def _run(base_url: str, *, backend_url: str, private_key: RSAPrivateKey) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    seen: list[str] = []
    state: dict[str, BrowserAuthMode | int] = {
        "session": "anonymous",
        "my_tools_status": 200,
    }
    local_user_id = seed_huleedu_projection(
        email="pr-0252-return-huleedu@example.test",
        display_name="Return Teacher",
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        jti="pr-0252-return-to-origin-context",
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
            state=state,
            seen=seen,
        )

        page.goto(f"{base_url}{PROTECTED_ROUTE}", wait_until="domcontentloaded")
        _expect_auth_login_next(page, base_url=base_url, next_path=PROTECTED_ROUTE)
        page.screenshot(path=str(ARTIFACTS_DIR / "anonymous-protected-entry.png"), full_page=True)

        state["session"] = "authenticated"
        state["my_tools_status"] = 401
        page.goto(f"{base_url}{PROTECTED_ROUTE}", wait_until="domcontentloaded")
        _expect_auth_login_next(page, base_url=base_url, next_path=PROTECTED_ROUTE)
        page.screenshot(path=str(ARTIFACTS_DIR / "revoked-session-recovery.png"), full_page=True)

        state["my_tools_status"] = 200
        page.goto(
            f"{base_url}/auth/login?next={PROTECTED_ROUTE}",
            wait_until="domcontentloaded",
        )
        _expect_editor(page, base_url=base_url)
        page.screenshot(path=str(ARTIFACTS_DIR / "successful-return-editor.png"), full_page=True)

        context.close()
        browser.close()

    required = {
        "huleedu-session:anonymous",
        "huleedu-session:authenticated",
        "app-continuation-live",
        "huleedu-csrf",
        "my-tools:401",
        "my-tools:200",
    }
    missing = required.difference(seen)
    if missing:
        raise AssertionError(f"Missing expected proof calls: {sorted(missing)}; seen={seen}")

    print(
        "playwright-pr-0252-auth-return-to-origin: ok "
        "direct /editor -> /auth/login?next=/editor; "
        "401 recovery preserved next; authenticated return resumed /editor"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0252 auth return-to-origin proof")
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
    verifier_public_key = public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"Invalid --base-url: {base_url}")
        _run(base_url.rstrip("/"), backend_url=backend_url, private_key=private_key)

    if args.start_backend:
        with temporary_backend_server(
            verifier_public_key,
            artifacts_dir=ARTIFACTS_DIR,
        ) as backend_url:
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
