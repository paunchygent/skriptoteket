"""Shared Playwright helpers for HuleEdu-auth cutover proofs.

Purpose:
    Provide reusable local proof helpers for EPIC-28 browser-session checks:
    temporary Vite/backend servers, signed HuleEdu Gateway identity headers,
    deterministic local projection seeding, and real continuation-route probes.

Relationships:
    - Targeted PR Playwright entrypoints import this module instead of
      importing from one another.
    - The helpers exercise the same HuleEdu-derived app-continuation boundary
      implemented for `PR-0255` and consumed by later EPIC-28 slices.
"""

from __future__ import annotations

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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from playwright.sync_api import APIRequestContext, Page, Playwright, Route

DEFAULT_PROVIDER_SUBJECT = "huleedu-provider-subject"
DEFAULT_PROVIDER_EMAIL = "pr-live-huleedu@example.test"
DEFAULT_PROVIDER_DISPLAY_NAME = "Local Teacher"
DEFAULT_LOCAL_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_SIGNING_KEY_ID = "gateway-identity-rs256-v1"
DEFAULT_BROWSER_SESSION_EXPIRES_AT = "2026-04-30T12:30:00Z"


@dataclass(frozen=True)
class HuleEduSignedSession:
    """Signed local proof context for request-level and browser checks."""

    api_session: requests.Session
    signed_headers: dict[str, str]
    local_user_id: UUID
    provider_subject: str
    provider_email: str
    display_name: str
    public_key: str


def repo_root() -> Path:
    """Return the repository root for src-path setup and subprocess cwd."""
    return Path(__file__).resolve().parents[1]


def backend_url_for_spa(base_url: str) -> str:
    """Derive the backend URL for the usual Vite dev-server path."""
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _ensure_src_import_path() -> None:
    """Allow targeted scripts to import the local src-layout package."""
    src_dir = repo_root() / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _free_port() -> int:
    """Return an available localhost TCP port for a temporary Vite server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, *, timeout_seconds: float = 20.0) -> None:
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
def temporary_vite_server(*, proxy_target: str | None = None) -> Iterator[str]:
    """Start a temporary Vite dev server and stop it when the check ends."""
    port = _free_port()
    effective_proxy_target = proxy_target or os.environ.get(
        "VITE_DEV_PROXY_TARGET", "http://127.0.0.1:8000"
    )
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
        cwd=repo_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={
            **os.environ,
            "VITE_DEV_PROXY_TARGET": effective_proxy_target,
            "VITE_DEV_PUBLIC_API_PROXY_TARGET": effective_proxy_target,
        },
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        wait_http(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


@contextmanager
def temporary_backend_server(
    public_key_pem_value: str,
    *,
    artifacts_dir: Path,
    signing_key_id: str = DEFAULT_SIGNING_KEY_ID,
    port: int | None = 8000,
) -> Iterator[str]:
    """Start the repo's real dev backend with the HuleEdu verifier key."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    backend_log = artifacts_dir / "backend.log"
    log_handle = backend_log.open("w", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY": public_key_pem_value,
            "HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID": signing_key_id,
            "HULEEDU_INTERNAL_IDENTITY_ISSUER": "api_gateway_service",
            "HULEEDU_INTERNAL_IDENTITY_AUDIENCE": "skriptoteket",
            "ARTIFACTS_ROOT": env.get("ARTIFACTS_ROOT", "/tmp/skriptoteket/artifacts"),
        }
    )
    Path(env["ARTIFACTS_ROOT"]).mkdir(parents=True, exist_ok=True)
    live_port = _free_port() if port is None else port
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            "src",
            "skriptoteket.web.app:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(live_port),
        ],
        cwd=repo_root(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    base_url = f"http://127.0.0.1:{live_port}"
    try:
        try:
            wait_http(f"{base_url}/openapi.json", timeout_seconds=45)
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


def new_private_key() -> rsa.RSAPrivateKey:
    """Create a temporary RS256 key for local signed-context proofs."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def public_key_pem(private_key: rsa.RSAPrivateKey) -> str:
    """Return the PEM public key for a temporary HuleEdu verifier."""
    return (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes with unpadded base64url."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def signed_identity_headers(
    *,
    private_key: rsa.RSAPrivateKey,
    subject: str = DEFAULT_PROVIDER_SUBJECT,
    now_ts: int | None = None,
    jti: str = "playwright-huleedu-context",
    product_identity_realm: str = "skriptoteket_standalone",
    email: str = "pr-live-huleedu@example.test",
    email_verified: bool | str | None = True,
    display_name: str = "Local Teacher",
    payload_removed_fields: tuple[str, ...] = (),
) -> dict[str, str]:
    """Build signed HuleEdu Gateway headers for a local proof request."""
    issued_at = now_ts or int(datetime.now(timezone.utc).timestamp())
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
        "iat": issued_at,
        "exp": issued_at + 60,
        "jti": jti,
        "active_context": {"org_id": "org-1", "tenant_id": "tenant-1"},
        "feature_flags": ["inline-completion"],
        "source_app": "huleedu-browser",
        "active_app": "skriptoteket",
        "active_product_identity_realm": product_identity_realm,
        "realm_subject_id": subject,
        "linked_identity_ids": {product_identity_realm: subject},
        "email": email,
        "email_verified": True,
        "given_name": "Local",
        "family_name": "Teacher",
        "display_name": display_name,
        "locale": "sv-SE",
    }
    if email_verified is not True:
        payload["email_verified"] = email_verified
    for field_name in payload_removed_fields:
        payload.pop(field_name, None)
    encoded_context = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = private_key.sign(
        encoded_context.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return {
        "X-HuleEdu-Identity-Context-Version": "1",
        "X-HuleEdu-Identity-Context": encoded_context,
        "X-HuleEdu-Identity-Key-Id": DEFAULT_SIGNING_KEY_ID,
        "X-HuleEdu-Identity-Signature": f"rs256={_b64url_encode(signature)}",
    }


async def _seed_huleedu_projection(
    *,
    local_user_id: str,
    provider_subject: str,
    email: str,
    display_name: str,
    role: str = "contributor",
) -> UUID:
    """Seed a deterministic local projection through the real database schema."""
    _ensure_src_import_path()

    from sqlalchemy.dialects.postgresql import insert

    from skriptoteket.cli._db import open_session
    from skriptoteket.config import Settings
    from skriptoteket.infrastructure.db.models.identity_projection import IdentityProjectionModel
    from skriptoteket.infrastructure.db.models.user import UserModel
    from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel

    now = datetime.now(timezone.utc)
    async with open_session(Settings()) as session:
        user_stmt = (
            insert(UserModel)
            .values(
                id=UUID(local_user_id),
                email=email,
                role=role,
                auth_provider="huleedu",
                password_hash=None,
                is_active=True,
                email_verified=True,
                failed_login_attempts=0,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[UserModel.email],
                set_={
                    "email": email,
                    "role": role,
                    "auth_provider": "huleedu",
                    "is_active": True,
                    "email_verified": True,
                    "failed_login_attempts": 0,
                    "updated_at": now,
                },
            )
            .returning(UserModel.id)
        )
        seeded_user_id = (await session.execute(user_stmt)).scalar_one()
        projection_stmt = (
            insert(IdentityProjectionModel)
            .values(
                user_id=seeded_user_id,
                product_identity_realm="skriptoteket_standalone",
                realm_subject_id=provider_subject,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_identity_projections_realm_subject",
                set_={
                    "user_id": seeded_user_id,
                    "updated_at": now,
                },
            )
        )
        await session.execute(projection_stmt)
        profile_stmt = (
            insert(UserProfileModel)
            .values(
                user_id=seeded_user_id,
                display_name=display_name,
                locale="sv-SE",
                allow_remote_fallback=True,
                inline_completion_provider="external",
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[UserProfileModel.user_id],
                set_={
                    "display_name": display_name,
                    "locale": "sv-SE",
                    "allow_remote_fallback": True,
                    "inline_completion_provider": "external",
                    "updated_at": now,
                },
            )
        )
        await session.execute(profile_stmt)
        await session.commit()
        return seeded_user_id


def seed_huleedu_projection(
    *,
    local_user_id: str = DEFAULT_LOCAL_USER_ID,
    provider_subject: str = DEFAULT_PROVIDER_SUBJECT,
    email: str = "pr-live-huleedu@example.test",
    display_name: str = "Local Teacher",
    role: str = "contributor",
) -> UUID:
    """Synchronously seed the local HuleEdu-linked projection for Playwright."""
    return asyncio.run(
        _seed_huleedu_projection(
            local_user_id=local_user_id,
            provider_subject=provider_subject,
            email=email,
            display_name=display_name,
            role=role,
        )
    )


def create_signed_huleedu_api_session(
    *,
    private_key: rsa.RSAPrivateKey | None = None,
    local_user_id: str = DEFAULT_LOCAL_USER_ID,
    provider_subject: str = DEFAULT_PROVIDER_SUBJECT,
    email: str = DEFAULT_PROVIDER_EMAIL,
    display_name: str = DEFAULT_PROVIDER_DISPLAY_NAME,
    role: str = "contributor",
    jti: str = "playwright-local-huleedu-context",
) -> HuleEduSignedSession:
    """Create a requests session authenticated by signed HuleEdu context.

    The backend under test must trust the returned ``public_key``. For fully
    self-contained local proofs, start the backend with ``temporary_backend_server``.
    """
    signing_key = private_key or new_private_key()
    local_projection_id = seed_huleedu_projection(
        local_user_id=local_user_id,
        provider_subject=provider_subject,
        email=email,
        display_name=display_name,
        role=role,
    )
    signed_headers = signed_identity_headers(
        private_key=signing_key,
        subject=provider_subject,
        email=email,
        display_name=display_name,
        jti=jti,
    )
    session = requests.Session()
    session.headers.update(signed_headers)
    return HuleEduSignedSession(
        api_session=session,
        signed_headers=signed_headers,
        local_user_id=local_projection_id,
        provider_subject=provider_subject,
        provider_email=email,
        display_name=display_name,
        public_key=public_key_pem(signing_key),
    )


def install_local_huleedu_auth_routes(
    page: Page,
    *,
    base_url: str,
    signed_headers: dict[str, str],
    provider_subject: str = DEFAULT_PROVIDER_SUBJECT,
    provider_email: str = DEFAULT_PROVIDER_EMAIL,
    display_name: str = DEFAULT_PROVIDER_DISPLAY_NAME,
    seen: list[str] | None = None,
) -> None:
    """Mock HuleEdu browser auth and sign local protected app API requests."""
    cors_headers = {
        "content-type": "application/json",
        "access-control-allow-origin": base_url,
        "access-control-allow-credentials": "true",
    }

    def huleedu_session(route: Route) -> None:
        if seen is not None:
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
                    "profile": {"display_name": display_name, "locale": "sv-SE"},
                    "context": {
                        "active_app": "skriptoteket",
                        "active_product_identity_realm": "skriptoteket_standalone",
                        "realm_subject_id": provider_subject,
                    },
                    "policy": {
                        "roles": ["teacher"],
                        "grants": ["tools:run"],
                        "feature_flags": ["inline-completion"],
                    },
                    "session": {
                        "transport": "cookie",
                        "csrf_required": True,
                        "expires_at": DEFAULT_BROWSER_SESSION_EXPIRES_AT,
                    },
                }
            ),
        )

    def huleedu_csrf(route: Route) -> None:
        if seen is not None:
            seen.append("huleedu-csrf")
        route.fulfill(
            status=200,
            headers=cors_headers,
            body=json.dumps({"csrf_token": "csrf-token"}),
        )

    def protected_app_api(route: Route) -> None:
        if seen is not None and "/api/v1/profile/app-continuation" in route.request.url:
            seen.append("app-continuation-live")
        route.continue_(headers={**route.request.headers, **signed_headers})

    page.route("https://api.hule.education/v1/auth/session", huleedu_session)
    page.route("https://api.hule.education/v1/auth/csrf", huleedu_csrf)
    page.route("**/api/v1/**", protected_app_api)


def open_local_huleedu_app(page: Page, *, base_url: str, path: str) -> None:
    """Open a protected SPA path after installing local HuleEdu auth routes."""
    page.goto(f"{base_url.rstrip('/')}{path}", wait_until="domcontentloaded")


def verify_profile_continuation_api(
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
