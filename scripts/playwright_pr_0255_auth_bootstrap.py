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
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from playwright.sync_api import APIRequestContext, Page, Playwright, expect, sync_playwright

from scripts._playwright_browser import launch_chromium

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0255-auth-bootstrap")
PROVIDER_SUBJECT = "huleedu-provider-subject"
LOCAL_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
SIGNING_KEY_ID = "gateway-identity-rs256-v1"


def _repo_root() -> Path:
    """Return the repository root for src-path setup and subprocess cwd."""
    return Path(__file__).resolve().parents[1]


def _ensure_src_import_path() -> None:
    """Allow this targeted script to import the local src-layout package."""
    src_dir = _repo_root() / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _backend_url_for_spa(base_url: str) -> str:
    """Derive the backend URL for the usual Vite dev-server path."""
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _free_port() -> int:
    """Return an available localhost TCP port for a temporary Vite server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http(url: str, *, timeout_seconds: float = 20.0) -> None:
    """Wait until a local HTTP endpoint answers."""
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except Exception as exc:  # noqa: BLE001 - diagnostic wait loop
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


@contextmanager
def _temporary_vite_server() -> Iterator[str]:
    """Start a temporary Vite dev server and stop it when the check ends."""
    port = _free_port()
    process = subprocess.Popen(
        [
            "pnpm",
            "-C",
            "frontend",
            "--filter",
            "@skriptoteket/spa",
            "exec",
            "vite",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ],
        cwd=_repo_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


@contextmanager
def _temporary_backend_server(public_key_pem: str) -> Iterator[str]:
    """Start the repo's real dev backend with the PR-0255 verifier key."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    backend_log = ARTIFACTS_DIR / "backend.log"
    log_handle = backend_log.open("w", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY": public_key_pem,
            "HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID": SIGNING_KEY_ID,
            "HULEEDU_INTERNAL_IDENTITY_ISSUER": "api_gateway_service",
            "HULEEDU_INTERNAL_IDENTITY_AUDIENCE": "skriptoteket",
            "ARTIFACTS_ROOT": env.get("ARTIFACTS_ROOT", "/tmp/skriptoteket/artifacts"),
        }
    )
    Path(env["ARTIFACTS_ROOT"]).mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        ["pdm", "run", "dev"],
        cwd=_repo_root(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    base_url = "http://127.0.0.1:8000"
    try:
        try:
            _wait_http(f"{base_url}/openapi.json", timeout_seconds=45)
        except RuntimeError as exc:
            log_handle.flush()
            tail = "\n".join(backend_log.read_text(encoding="utf-8").splitlines()[-40:])
            raise RuntimeError(f"{exc}\nBackend log tail:\n{tail}") from exc
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log_handle.close()


def _public_key_pem(private_key: rsa.RSAPrivateKey) -> str:
    return (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _signed_identity_headers(
    *,
    private_key: rsa.RSAPrivateKey,
    subject: str,
    now_ts: int,
) -> dict[str, str]:
    """Build signed HuleEdu Gateway headers for a local proof request."""
    payload = {
        "context_version": 1,
        "iss": "api_gateway_service",
        "aud": "skriptoteket",
        "sub": subject,
        "session_id": "huleedu-live-session",
        "org_id": "org-1",
        "tenant_id": "tenant-1",
        "roles": ["teacher"],
        "grants": ["tools:run"],
        "policy_version": "2026-04-11",
        "iat": now_ts,
        "exp": now_ts + 60,
        "jti": "pr-0255-live-context",
        "active_context": {"org_id": "org-1", "tenant_id": "tenant-1"},
        "feature_flags": ["inline-completion"],
        "source_app": "huleedu-browser",
    }
    encoded_context = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = private_key.sign(
        encoded_context.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return {
        "X-Huledu-Identity-Context-Version": "1",
        "X-Huledu-Identity-Context": encoded_context,
        "X-Huledu-Identity-Key-Id": SIGNING_KEY_ID,
        "X-Huledu-Identity-Signature": f"rs256={_b64url_encode(signature)}",
    }


async def _seed_huleedu_projection() -> UUID:
    """Seed a deterministic local projection through the real database schema."""
    _ensure_src_import_path()

    from sqlalchemy.dialects.postgresql import insert

    from skriptoteket.cli._db import open_session
    from skriptoteket.config import Settings
    from skriptoteket.infrastructure.db.models.user import UserModel
    from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel

    now = datetime.now(timezone.utc)
    async with open_session(Settings()) as session:
        user_stmt = (
            insert(UserModel)
            .values(
                id=UUID(LOCAL_USER_ID),
                email="pr-0255-live-huleedu@example.test",
                role="contributor",
                auth_provider="huleedu",
                external_id=PROVIDER_SUBJECT,
                password_hash=None,
                is_active=True,
                email_verified=True,
                failed_login_attempts=0,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_users_auth_provider_external_id",
                set_={
                    "email": "pr-0255-live-huleedu@example.test",
                    "role": "contributor",
                    "is_active": True,
                    "email_verified": True,
                    "failed_login_attempts": 0,
                    "updated_at": now,
                },
            )
            .returning(UserModel.id)
        )
        local_user_id = (await session.execute(user_stmt)).scalar_one()
        profile_stmt = (
            insert(UserProfileModel)
            .values(
                user_id=local_user_id,
                display_name="Local Teacher",
                locale="sv-SE",
                allow_remote_fallback=True,
                inline_completion_provider="external",
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[UserProfileModel.user_id],
                set_={
                    "display_name": "Local Teacher",
                    "locale": "sv-SE",
                    "allow_remote_fallback": True,
                    "inline_completion_provider": "external",
                    "updated_at": now,
                },
            )
        )
        await session.execute(profile_stmt)
        await session.commit()
        return local_user_id


def _verify_profile_continuation_api(
    playwright: Playwright,
    *,
    backend_url: str,
    signed_headers: dict[str, str],
    local_user_id: UUID,
) -> None:
    """Verify the real continuation route on the real backend over HTTP."""
    request_context: APIRequestContext | None = None
    try:
        request_context = playwright.request.new_context(base_url=backend_url)
        valid = request_context.get(
            "/api/v1/profile/app-continuation",
            headers=signed_headers,
        )
        missing = request_context.get("/api/v1/profile/app-continuation")

        if valid.status != 200:
            raise AssertionError(f"Expected valid continuation 200, got {valid.status}")
        if valid.json()["local_user"]["id"] != str(local_user_id):
            raise AssertionError("Continuation did not return the Skriptoteket-local user id")
        if valid.json()["profile"]["user_id"] != str(local_user_id):
            raise AssertionError("Continuation profile did not match the local user id")
        if missing.status != 401:
            raise AssertionError(f"Expected missing-context continuation 401, got {missing.status}")
    finally:
        if request_context is not None:
            request_context.dispose()


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


def _run(base_url: str, *, backend_url: str, private_key: rsa.RSAPrivateKey) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    seen: list[str] = []
    local_user_id = asyncio.run(_seed_huleedu_projection())
    signed_headers = _signed_identity_headers(
        private_key=private_key,
        subject=PROVIDER_SUBJECT,
        now_ts=int(datetime.now(timezone.utc).timestamp()),
    )
    with sync_playwright() as playwright:
        _verify_profile_continuation_api(
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

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = _public_key_pem(private_key)

    def run_with_base_url(base_url: str, backend_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"Invalid --base-url: {base_url}")
        _run(base_url.rstrip("/"), backend_url=backend_url, private_key=private_key)

    if args.start_backend:
        with _temporary_backend_server(public_key) as backend_url:
            if args.start_vite:
                with _temporary_vite_server() as base_url:
                    run_with_base_url(base_url, backend_url)
                return
            run_with_base_url(args.base_url, backend_url)
        return

    if args.start_vite:
        with _temporary_vite_server() as base_url:
            run_with_base_url(base_url, _backend_url_for_spa(base_url))
        return

    run_with_base_url(args.base_url, _backend_url_for_spa(args.base_url))


if __name__ == "__main__":
    main()
