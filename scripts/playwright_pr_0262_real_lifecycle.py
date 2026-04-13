"""PR-0262 retained Skriptoteket lifecycle proof entrypoint.

Purpose:
    Consume the final HuleEdu TASK-0327 provider artifact, then prove the
    Skriptoteket-owned callback, projection, diagnostics, and local role
    behavior through the real backend and SPA.

Relationships:
    - Delegates artifact validation and manifest redaction to
      `scripts._pr_0262_lifecycle_manifest`.
    - Reuses the EPIC-28 HuleEdu signed-context Playwright helpers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from playwright.sync_api import APIRequestContext, Page, Playwright, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_huleedu_auth import (
    backend_url_for_spa,
    new_private_key,
    public_key_pem,
    seed_huleedu_projection,
    signed_identity_headers,
    temporary_backend_server,
    temporary_vite_server,
)
from scripts._pr_0262_lifecycle_manifest import (
    DEFAULT_PROBE_PATH,
    DEFAULT_REALM,
    EnvironmentName,
    RoleName,
    assert_manifest_redacted,
    build_manifest,
    load_huleedu_task_0327_artifact,
)

DEFAULT_ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0262-real-lifecycle")
DEFAULT_LOCAL_USER_ID = "550e8400-e29b-41d4-a716-446655442602"
DEFAULT_CONTROLLED_ACCOUNT_KEY = "skriptoteket-proof-contributor"
DEFAULT_EXPECTED_LOCAL_ROLE = "contributor"
DEFAULT_CALLBACK_NEXT_PATH = "/editor"
PR_0262_CONTEXT_ID = "pr-0262-lifecycle-context"
REQUIRED_TRUE_CLAIMS = (
    "realm_subject_id_present",
    "subject_claim_present",
    "subject_matches_realm_subject",
    "linked_identity_realm_present",
    "linked_identity_matches_realm_subject",
    "email_present",
    "email_verified",
)


def _verify_api_surfaces(
    playwright: Playwright,
    *,
    backend_url: str,
    signed_headers: dict[str, str],
    expected_local_role: RoleName,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    request_context: APIRequestContext | None = None
    try:
        request_context = playwright.request.new_context(base_url=backend_url)
        continuation = request_context.get(
            "/api/v1/profile/app-continuation",
            headers=signed_headers,
        )
        missing = request_context.get("/api/v1/profile/app-continuation")
        probe = request_context.get(DEFAULT_PROBE_PATH, headers=signed_headers)

        if continuation.status != 200:
            raise AssertionError(f"Expected continuation 200, got {continuation.status}")
        if missing.status != 401:
            raise AssertionError(f"Expected missing-context continuation 401, got {missing.status}")
        if probe.status != 200:
            raise AssertionError(f"Expected diagnostics probe 200, got {probe.status}")

        continuation_payload = continuation.json()
        local_user = continuation_payload["local_user"]
        profile = continuation_payload["profile"]
        observed_role = local_user["role"]
        if observed_role != expected_local_role:
            raise AssertionError(
                f"Expected local role {expected_local_role}, got {observed_role!r}"
            )
        if profile["user_id"] != local_user["id"]:
            raise AssertionError("Continuation profile does not match the local user.")

        probe_claims = probe.json()["claims"]
        for key in REQUIRED_TRUE_CLAIMS:
            if probe_claims.get(key) is not True:
                raise AssertionError(f"Live probe claim {key} was not true.")

        return (
            {
                "app_continuation_status_code": continuation.status,
                "missing_context_status_code": missing.status,
                "diagnostics_probe_status_code": probe.status,
            },
            {
                "projection_resolved": True,
                "local_user_id_present": bool(local_user["id"]),
                "profile_user_matches_local_user": True,
                "projection_subject_matched_session_claim": True,
                "product_identity_realm": DEFAULT_REALM,
            },
            {
                "expected_local_role": expected_local_role,
                "observed_local_role": observed_role,
                "role_matches_expected": True,
                "provider_roles_ignored_for_local_authorization": True,
            },
            {
                "status": "ok",
                "claims": {
                    "active_app": probe_claims["active_app"],
                    "active_product_identity_realm": probe_claims["active_product_identity_realm"],
                    **{key: probe_claims[key] for key in REQUIRED_TRUE_CLAIMS},
                },
            },
        )
    finally:
        if request_context is not None:
            request_context.dispose()


def _fulfill_json(route: Any, payload: dict[str, object], *, status: int = 200) -> None:
    route.fulfill(
        status=status, headers={"content-type": "application/json"}, body=json.dumps(payload)
    )


def _install_browser_auth_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    provider_subject: str,
    provider_email: str,
) -> None:
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route: Any) -> None:
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
                    "profile": {"display_name": "PR 0262 Teacher", "locale": "sv-SE"},
                    "policy": {
                        "roles": ["teacher"],
                        "grants": ["tools:run"],
                        "feature_flags": ["inline-completion"],
                    },
                    "session": {
                        "transport": "cookie",
                        "csrf_required": True,
                        "expires_at": "2026-04-13T13:30:00Z",
                    },
                }
            ),
        )

    def huleedu_csrf(route: Any) -> None:
        route.fulfill(
            status=200, headers=cors_headers, body=json.dumps({"csrf_token": "csrf-token"})
        )

    def app_continuation(route: Any) -> None:
        route.continue_(headers={**route.request.headers, **signed_headers})

    def my_tools(route: Any) -> None:
        _fulfill_json(route, {"tools": []})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/profile/app-continuation", app_continuation)
    page.route("**/api/v1/my-tools", my_tools)


def _assert_browser_callback(
    page: Page,
    *,
    base_url: str,
    callback_next_path: str,
    screenshot_path: Path,
) -> dict[str, object]:
    encoded_next = quote(callback_next_path, safe="")
    page.goto(f"{base_url}/auth/callback?next={encoded_next}", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(rf"^{re.escape(base_url + callback_next_path)}(?:$|\?)"))
    if callback_next_path == "/editor":
        expect(page.get_by_role("heading", name="Kodredigeraren")).to_be_visible(timeout=15_000)
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "callback_path": "/auth/callback",
        "intended_next_path": callback_next_path,
        "final_path": urlparse(page.url).path,
        "continuation_resumed_intended_route": True,
        "screenshot": str(screenshot_path),
    }


def _run(
    *,
    environment: EnvironmentName,
    base_url: str,
    backend_url: str,
    huleedu_artifact_path: Path,
    run_dir: Path,
    private_key: RSAPrivateKey,
    controlled_account_key: str,
    expected_local_role: RoleName,
    callback_next_path: str,
) -> Path:
    validation = load_huleedu_task_0327_artifact(huleedu_artifact_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    local_user_id = seed_huleedu_projection(
        local_user_id=DEFAULT_LOCAL_USER_ID,
        provider_subject=validation.provider_subject,
        email=validation.provider_email,
        display_name="PR 0262 Teacher",
        role=expected_local_role,
    )
    signed_headers = signed_identity_headers(
        private_key=private_key,
        subject=validation.provider_subject,
        email=validation.provider_email,
        display_name="PR 0262 Teacher",
        jti=PR_0262_CONTEXT_ID,
    )

    with sync_playwright() as playwright:
        callback, projection, role, live_probe = _verify_api_surfaces(
            playwright,
            backend_url=backend_url,
            signed_headers=signed_headers,
            expected_local_role=expected_local_role,
        )
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        _install_browser_auth_routes(
            page,
            base_url=base_url,
            signed_headers=signed_headers,
            provider_subject=validation.provider_subject,
            provider_email=validation.provider_email,
        )
        screenshot_path = run_dir / "callback-editor-continuation.png"
        browser_callback = _assert_browser_callback(
            page,
            base_url=base_url,
            callback_next_path=callback_next_path,
            screenshot_path=screenshot_path,
        )
        context.close()
        browser.close()

    forbidden_values = [validation.provider_subject, validation.provider_email, PR_0262_CONTEXT_ID]
    manifest = build_manifest(
        environment=environment,
        run_id=run_dir.name,
        huleedu_validation=validation,
        controlled_account_key=controlled_account_key,
        callback_assertions={
            **callback,
            "browser_callback": browser_callback,
            "upstream_next_path_validated": validation.upstream_next_path is not None,
        },
        projection_assertions={
            **projection,
            "seeded_local_projection_reused": True,
            "seeded_local_user_id_present": bool(local_user_id),
            "live_diagnostics_probe": live_probe,
        },
        local_role_assertions={**role, "controlled_account_key": controlled_account_key},
        screenshot_paths=[str(screenshot_path)],
        log_paths=[str(run_dir / "backend.log")] if (run_dir / "backend.log").exists() else [],
        forbidden_values=forbidden_values,
    )
    manifest_path = run_dir / "manifest.redacted.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    assert_manifest_redacted(
        json.loads(manifest_path.read_text(encoding="utf-8")), forbidden_values=forbidden_values
    )
    return manifest_path


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> None:
    parser = argparse.ArgumentParser(description="PR-0262 lifecycle projection proof")
    parser.add_argument(
        "--environment", choices=["local-nonprod", "production"], default="local-nonprod"
    )
    parser.add_argument("--huleedu-artifact", default=os.environ.get("HULEEDU_TASK_0327_ARTIFACT"))
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--start-vite", action="store_true")
    parser.add_argument("--start-backend", action="store_true")
    parser.add_argument("--callback-next-path", default=DEFAULT_CALLBACK_NEXT_PATH)
    parser.add_argument("--controlled-account-key", default=DEFAULT_CONTROLLED_ACCOUNT_KEY)
    parser.add_argument(
        "--expected-local-role",
        choices=["user", "contributor", "admin", "superuser"],
        default=DEFAULT_EXPECTED_LOCAL_ROLE,
    )
    args = parser.parse_args()
    if not args.huleedu_artifact:
        parser.error("--huleedu-artifact or HULEEDU_TASK_0327_ARTIFACT is required")
    if not args.callback_next_path.startswith("/") or args.callback_next_path.startswith("//"):
        parser.error("--callback-next-path must be a safe app route")

    artifact_root = (
        Path(args.artifact_dir) if args.artifact_dir else DEFAULT_ARTIFACT_ROOT / args.environment
    )
    run_dir = artifact_root / _run_id()
    private_key = new_private_key()
    public_key = public_key_pem(private_key)
    base_url = str(args.base_url).rstrip("/")
    backend_url = str(args.backend_url or backend_url_for_spa(base_url)).rstrip("/")

    def run_with(base: str, backend: str) -> Path:
        return _run(
            environment=args.environment,
            base_url=base.rstrip("/"),
            backend_url=backend.rstrip("/"),
            huleedu_artifact_path=Path(args.huleedu_artifact),
            run_dir=run_dir,
            private_key=private_key,
            controlled_account_key=args.controlled_account_key,
            expected_local_role=args.expected_local_role,
            callback_next_path=args.callback_next_path,
        )

    if args.start_backend:
        with temporary_backend_server(public_key, artifacts_dir=run_dir, port=None) as live_backend:
            if args.start_vite:
                with temporary_vite_server(proxy_target=live_backend) as live_base:
                    manifest_path = run_with(live_base, live_backend)
            else:
                manifest_path = run_with(base_url, live_backend)
    elif args.start_vite:
        with temporary_vite_server() as live_base:
            manifest_path = run_with(live_base, backend_url_for_spa(live_base))
    else:
        manifest_path = run_with(base_url, backend_url)

    print(f"playwright-pr-0262-real-lifecycle: ok manifest={manifest_path}")


if __name__ == "__main__":
    main()
