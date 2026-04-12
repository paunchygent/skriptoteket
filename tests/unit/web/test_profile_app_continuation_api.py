"""Profile continuation route tests.

Purpose:
    Verify the app-local bootstrap continuation contract used after HuleEdu
    shared-session bootstrap.

Relationships:
    - Exercises `src.skriptoteket.web.api.v1.profile` through FastAPI.
    - Uses the real HuleEdu internal identity verifier and local projection
      resolver with protocol stubs for persistence.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import make_async_container
from fastapi import Depends, FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.domain.errors import ErrorCode
from skriptoteket.domain.identity.internal_identity_context import (
    INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
    INTERNAL_IDENTITY_KEY_ID_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_PREFIX,
)
from skriptoteket.domain.identity.models import AuthProvider, User
from skriptoteket.web.api.v1 import profile as profile_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_user_profile
from tests.fixtures.profile_app_continuation_support import (
    CONTEXT_SUBJECT,
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    b64url_encode,
    build_headers,
    huleedu_user,
)


@pytest.fixture
def clock() -> ClockStub:
    return ClockStub(datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(private_key: rsa.RSAPrivateKey) -> Settings:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    settings = Settings()
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = public_key.decode("utf-8")
    return settings


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(profile_api.router)

    @app.get("/api/v1/pr-0253/protected-read")
    async def protected_read(user: User = Depends(require_app_user_api)) -> dict[str, str]:
        return {"user_id": str(user.id)}

    @app.post("/api/v1/pr-0253/protected-write")
    async def protected_write(user: User = Depends(require_app_user_api)) -> dict[str, str]:
        return {"user_id": str(user.id)}

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_profile_app_continuation_accepts_valid_huleedu_context_without_local_session_cookie(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = huleedu_user()
    profile = make_user_profile(
        user_id=user.id,
        allow_remote_fallback=True,
        inline_completion_provider="external",
    )
    users.user = user
    profiles.result = profile

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
        ),
    )

    assert response.status_code == 200
    assert response.json() == {
        "local_user": user.model_dump(mode="json"),
        "profile": profile.model_dump(mode="json"),
        "ai_policy": {
            "remote_providers_enabled": True,
            "completion_external_available": False,
            "completion_local_available": True,
        },
        "allow_remote_fallback": True,
        "inline_completion_provider": "external",
    }
    assert users.lookup_calls == [(AuthProvider.HULEEDU, CONTEXT_SUBJECT)]
    assert profiles.get_by_user_id_calls == [user.id]


@pytest.mark.asyncio
async def test_profile_app_continuation_creates_missing_profile_for_existing_projection(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = huleedu_user()
    users.user = user

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
        ),
    )

    assert response.status_code == 200
    assert response.json()["profile"]["user_id"] == str(user.id)
    assert response.json()["allow_remote_fallback"] is None
    assert response.json()["inline_completion_provider"] is None
    assert profiles.created is not None
    assert profiles.created.user_id == user.id


@pytest.mark.asyncio
async def test_profile_app_continuation_fails_closed_without_local_projection(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
        ),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert response.json()["error"]["details"]["reason"] == "missing_huleedu_app_projection"
    assert users.lookup_calls == [(AuthProvider.HULEEDU, CONTEXT_SUBJECT)]


@pytest.mark.asyncio
async def test_app_dependency_rejects_stale_csrf_without_signed_huleedu_context(
    client: httpx.AsyncClient,
    users: UserRepositoryStub,
) -> None:
    users.user = huleedu_user()

    response = await client.post(
        "/api/v1/pr-0253/protected-write",
        headers={"X-CSRF-Token": "stale-local-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert users.lookup_calls == []


@pytest.mark.asyncio
async def test_app_dependency_accepts_signed_context_for_read_and_write_without_local_session(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = huleedu_user()
    users.user = user
    profiles.result = make_user_profile(user_id=user.id)
    headers = build_headers(
        private_key=private_key,
        now_ts=int(clock.now().timestamp()),
    )

    read_response = await client.get("/api/v1/pr-0253/protected-read", headers=headers)
    write_response = await client.post("/api/v1/pr-0253/protected-write", headers=headers)

    assert read_response.status_code == 200
    assert write_response.status_code == 200
    assert read_response.json() == {"user_id": str(user.id)}
    assert write_response.json() == {"user_id": str(user.id)}


InvalidHeadersBuilder = Callable[[rsa.RSAPrivateKey, int], dict[str, str]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_name", "headers_builder"),
    [
        pytest.param(
            "missing_context",
            lambda _private_key, _now_ts: {},
            id="missing-context",
        ),
        pytest.param(
            "unsupported_header_version",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                header_overrides={INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER: "2"},
            ),
            id="unsupported-header-version",
        ),
        pytest.param(
            "missing_key_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                header_overrides={INTERNAL_IDENTITY_KEY_ID_HEADER: " "},
            ),
            id="missing-key-id",
        ),
        pytest.param(
            "unknown_key_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                header_overrides={INTERNAL_IDENTITY_KEY_ID_HEADER: "unknown"},
            ),
            id="unknown-key-id",
        ),
        pytest.param(
            "invalid_signature",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                header_overrides={
                    INTERNAL_IDENTITY_SIGNATURE_HEADER: (
                        f"{INTERNAL_IDENTITY_SIGNATURE_PREFIX}invalid"
                    )
                },
            ),
            id="invalid-signature",
        ),
        pytest.param(
            "malformed_payload",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                encoded_context=b64url_encode(b"not-json"),
            ),
            id="malformed-payload",
        ),
        pytest.param(
            "wrong_issuer",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"iss": "other-gateway"},
            ),
            id="wrong-issuer",
        ),
        pytest.param(
            "wrong_audience",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"aud": "other-service"},
            ),
            id="wrong-audience",
        ),
        pytest.param(
            "missing_org_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_removed_fields=("org_id",),
            ),
            id="missing-org-id",
        ),
        pytest.param(
            "blank_org_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"org_id": " "},
            ),
            id="blank-org-id",
        ),
        pytest.param(
            "missing_tenant_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_removed_fields=("tenant_id",),
            ),
            id="missing-tenant-id",
        ),
        pytest.param(
            "blank_tenant_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"tenant_id": " "},
            ),
            id="blank-tenant-id",
        ),
        pytest.param(
            "missing_roles",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_removed_fields=("roles",),
            ),
            id="missing-roles",
        ),
        pytest.param(
            "blank_role",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"roles": ["teacher", " "]},
            ),
            id="blank-role",
        ),
        pytest.param(
            "missing_grants",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_removed_fields=("grants",),
            ),
            id="missing-grants",
        ),
        pytest.param(
            "blank_grant",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"grants": ["tools:run", " "]},
            ),
            id="blank-grant",
        ),
        pytest.param(
            "expired_context",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"iat": now_ts - 120, "exp": now_ts - 10},
            ),
            id="expired-context",
        ),
        pytest.param(
            "future_issued_context",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"iat": now_ts + 10, "exp": now_ts + 60},
            ),
            id="future-issued-context",
        ),
        pytest.param(
            "overlong_lifetime",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"iat": now_ts, "exp": now_ts + 61},
            ),
            id="overlong-lifetime",
        ),
    ],
)
async def test_profile_app_continuation_rejects_invalid_huleedu_context(
    case_name: str,
    headers_builder: InvalidHeadersBuilder,
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    users.user = huleedu_user()

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=headers_builder(private_key, int(clock.now().timestamp())),
    )

    assert response.status_code == 401, case_name
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
