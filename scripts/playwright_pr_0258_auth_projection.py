"""PR-0258 live proof for realm-aware projection provisioning.

Purpose:
    Exercise the real app-continuation backend route with signed HuleEdu
    product-realm claims and prove first-login provisioning is idempotent.

Relationships:
    - Uses the shared HuleEdu signed-context helper from `_playwright_huleedu_auth`.
    - Complements Docker migration tests by proving runtime continuation uses
      `(product_identity_realm, realm_subject_id)` rather than `users.external_id`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import APIRequestContext, Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import (
    DEFAULT_PROVIDER_SUBJECT,
    backend_url_for_spa,
    new_private_key,
    public_key_pem,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0258-auth-projection")
PROVIDER_SUBJECT = f"{DEFAULT_PROVIDER_SUBJECT}-pr-0258"
PROVIDER_EMAIL = "pr-0258-provisioned@example.test"


def _fulfill_json(route, payload: dict[str, object], *, status: int = 200) -> None:
    route.fulfill(
        status=status,
        headers={"content-type": "application/json"},
        body=json.dumps(payload),
    )


def _verify_provisioning_api(
    request_context: APIRequestContext,
    *,
    private_key: RSAPrivateKey,
) -> str:
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        jti="pr-0258-first-login",
    )
    first = request_context.get("/api/v1/profile/app-continuation", headers=signed_headers)
    second = request_context.get("/api/v1/profile/app-continuation", headers=signed_headers)
    missing_email = request_context.get(
        "/api/v1/profile/app-continuation",
        headers=signed_identity_headers(
            private_key=private_key,
            subject=f"{PROVIDER_SUBJECT}-missing-email",
            email="missing-email@example.test",
            jti="pr-0258-missing-email",
            payload_removed_fields=("email",),
        ),
    )
    duplicate_email = request_context.get(
        "/api/v1/profile/app-continuation",
        headers=signed_identity_headers(
            private_key=private_key,
            subject=f"{PROVIDER_SUBJECT}-duplicate-email",
            email=PROVIDER_EMAIL,
            jti="pr-0258-duplicate-email",
        ),
    )

    if first.status != 200:
        raise AssertionError(f"Expected first provisioning 200, got {first.status}: {first.text()}")
    first_payload = first.json()
    local_user = first_payload["local_user"]
    if local_user["role"] != "user":
        raise AssertionError(f"Expected default local user role, got {local_user['role']!r}")
    if local_user["email"] != PROVIDER_EMAIL:
        raise AssertionError(f"Expected signed email {PROVIDER_EMAIL}, got {local_user['email']!r}")
    if first_payload["profile"]["display_name"] != "Local Teacher":
        raise AssertionError("Expected signed display_name to seed the profile")

    if second.status != 200:
        raise AssertionError(f"Expected second provisioning 200, got {second.status}")
    if second.json()["local_user"]["id"] != local_user["id"]:
        raise AssertionError("Expected repeated callback to reuse the same local projection")

    if missing_email.status != 401:
        raise AssertionError(f"Expected missing signed email 401, got {missing_email.status}")
    if missing_email.json()["error"]["details"].get("field") != "email":
        raise AssertionError("Missing-email failure did not report the email field")

    if duplicate_email.status != 401:
        raise AssertionError(f"Expected duplicate email 401, got {duplicate_email.status}")
    if duplicate_email.json()["error"]["details"].get("reason") != "identity_linking_required":
        raise AssertionError("Duplicate email did not fail closed into linking-required")

    return str(local_user["id"])


def _install_spa_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    seen: list[str],
) -> None:
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
                        "email": PROVIDER_EMAIL,
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
                        "expires_at": "2026-04-12T12:30:00Z",
                    },
                }
            ),
        )

    def huleedu_csrf(route) -> None:
        seen.append("huleedu-csrf")
        route.fulfill(status=200, headers=cors_headers, body=json.dumps({"csrf_token": "csrf"}))

    def app_continuation(route) -> None:
        seen.append("app-continuation-live")
        route.continue_(headers={**route.request.headers, **signed_headers})

    def catalog_tools(route) -> None:
        seen.append("catalog-tools")
        _fulfill_json(route, {"items": [], "professions": [], "categories": []})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/profile/app-continuation", app_continuation)
    page.route("**/api/v1/catalog/tools**", catalog_tools)


def _verify_spa_bootstrap(base_url: str, *, private_key: RSAPrivateKey) -> None:
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        email=PROVIDER_EMAIL,
        jti="pr-0258-spa-bootstrap",
    )
    seen: list[str] = []
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        _install_spa_routes(page, base_url=base_url, signed_headers=signed_headers, seen=seen)
        page.goto(f"{base_url}/browse", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Katalog")).to_be_visible(timeout=15_000)
        page.screenshot(path=str(ARTIFACTS_DIR / "browse-provisioned-user.png"), full_page=True)
        context.close()
        browser.close()

    required = {"huleedu-session", "app-continuation-live", "huleedu-csrf", "catalog-tools"}
    missing = required.difference(seen)
    if missing:
        raise AssertionError(f"Missing expected SPA calls: {sorted(missing)}")


def _assert_login_ceremony_url(
    url: str | None,
    *,
    base_url: str,
    expected_next: str | None,
) -> None:
    if not url:
        raise AssertionError("Expected a browser-navigable HuleEdu login ceremony URL.")
    if url.startswith(f"{base_url}/auth/login"):
        raise AssertionError(
            "Expected direct HuleEdu login ceremony URL, not app-local /auth/login."
        )
    if "/v1/auth/login" in url:
        raise AssertionError("Expected browser ceremony URL, not POST-only /v1/auth/login API.")

    parsed = urlparse(url)
    if parsed.path != "/auth/login":
        raise AssertionError(f"Expected /auth/login ceremony path, got {parsed.path!r}.")
    query = parse_qs(parsed.query)
    if query.get("app") != ["skriptoteket"]:
        raise AssertionError(f"Expected app=skriptoteket, got {query.get('app')!r}.")
    if query.get("product_identity_realm") != ["skriptoteket_standalone"]:
        raise AssertionError(
            "Expected product_identity_realm=skriptoteket_standalone, "
            f"got {query.get('product_identity_realm')!r}."
        )

    return_to = query.get("return_to", [None])[0]
    return_to_parsed = urlparse(return_to or "")
    base_parsed = urlparse(base_url)
    if (
        return_to_parsed.scheme != base_parsed.scheme
        or return_to_parsed.netloc != base_parsed.netloc
    ):
        raise AssertionError(f"Expected return_to origin {base_url}, got {return_to!r}.")
    if return_to_parsed.path != "/auth/callback":
        raise AssertionError(f"Expected return_to /auth/callback, got {return_to!r}.")

    if expected_next is None:
        if "next" in query:
            raise AssertionError(f"Expected no next parameter, got {query['next']!r}.")
        return
    if query.get("next") != [expected_next]:
        raise AssertionError(f"Expected next={expected_next!r}, got {query.get('next')!r}.")


def _install_signed_out_auth_routes(page: Page, *, base_url: str) -> None:
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route) -> None:
        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps(
                {
                    "authenticated": False,
                    "user": None,
                    "profile": None,
                    "policy": None,
                    "session": {
                        "transport": "cookie",
                        "csrf_required": True,
                        "expires_at": None,
                    },
                }
            ),
        )

    def huleedu_csrf(route) -> None:
        route.fulfill(status=200, headers=cors_headers, body=json.dumps({"csrf_token": "csrf"}))

    def gateway_login(route) -> None:
        if route.request.url.startswith(f"{base_url}/auth/login"):
            route.continue_()
            return
        route.fulfill(
            status=200,
            headers={"content-type": "text/html"},
            body="<h1>Gateway login</h1>",
        )

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/auth/login**", gateway_login)


def _verify_login_handoff(base_url: str) -> None:
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        _install_signed_out_auth_routes(page, base_url=base_url)

        page.goto(base_url, wait_until="domcontentloaded")
        login_href = page.get_by_role("link", name="Logga in").first.get_attribute("href")
        _assert_login_ceremony_url(login_href, base_url=base_url, expected_next="/")

        page.goto(f"{base_url}/auth/login?next=/browse", wait_until="domcontentloaded")
        for _ in range(30):
            if "/auth/login" in page.url and not page.url.startswith(f"{base_url}/"):
                break
            page.wait_for_timeout(500)
        else:
            raise AssertionError(f"Expected auto-handoff to HuleEdu login, got {page.url!r}.")
        _assert_login_ceremony_url(page.url, base_url=base_url, expected_next="/browse")
        page.screenshot(path=str(ARTIFACTS_DIR / "login-auto-handoff.png"), full_page=True)

        context.close()
        browser.close()


def _run(base_url: str, *, backend_url: str, private_key: RSAPrivateKey) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        request_context = playwright.request.new_context(base_url=backend_url)
        try:
            local_user_id = _verify_provisioning_api(
                request_context,
                private_key=private_key,
            )
        finally:
            request_context.dispose()

    _verify_spa_bootstrap(base_url, private_key=private_key)
    _verify_login_handoff(base_url)
    print(
        "playwright-pr-0258-auth-projection: ok "
        f"first-login provisioned local user {local_user_id}; repeated callback reused projection; "
        "missing signed email and duplicate email failed closed; login handoff opened the ceremony "
        "directly"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0258 auth projection proof")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="Running SPA base URL; ignored when --start-vite is set.",
    )
    parser.add_argument(
        "--gateway-base-url",
        default="https://api.hule.education",
        help="Documentary HuleEdu Gateway base URL used for local/non-production proof context.",
    )
    parser.add_argument("--start-vite", action="store_true")
    parser.add_argument("--start-backend", action="store_true")
    args = parser.parse_args()

    private_key = new_private_key()
    public_key = public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"Invalid --base-url: {base_url}")
        gateway = urlparse(args.gateway_base_url)
        if gateway.scheme not in {"http", "https"} or not gateway.netloc:
            raise SystemExit(f"Invalid --gateway-base-url: {args.gateway_base_url}")
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
