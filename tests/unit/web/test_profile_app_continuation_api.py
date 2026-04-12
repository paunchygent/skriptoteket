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
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1 import profile as profile_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_user_profile
from tests.fixtures.profile_app_continuation_support import (
    CONTEXT_SUBJECT,
    ClockStub,
    JsonValue,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    b64url_encode,
    build_headers,
    huleedu_user,
    seed_huleedu_projection,
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
    user = seed_huleedu_projection(users=users, profiles=profiles)
    profile = make_user_profile(
        user_id=user.id,
        allow_remote_fallback=True,
        inline_completion_provider="external",
    )
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
    assert users.projections.lookup_calls == [("skriptoteket_standalone", CONTEXT_SUBJECT)]
    assert profiles.get_by_user_id_calls == [user.id]


@pytest.mark.asyncio
async def test_profile_app_continuation_creates_missing_profile_for_existing_projection(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles)
    profiles.result = None

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
async def test_profile_app_continuation_provisions_missing_projection_from_signed_claims(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
        ),
    )

    assert response.status_code == 200
    assert response.json()["local_user"]["role"] == "user"
    assert response.json()["local_user"]["auth_provider"] == "huleedu"
    assert response.json()["local_user"]["email"] == "teacher@example.test"
    assert response.json()["profile"]["display_name"] == "Local Teacher"
    assert users.projections.created[0].realm_subject_id == CONTEXT_SUBJECT
    assert profiles.created is not None


@pytest.mark.asyncio
async def test_profile_app_continuation_fails_closed_without_signed_provisioning_claims(
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
            payload_removed_fields=("email",),
        ),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert response.json()["error"]["details"] == {
        "reason": "missing_huleedu_app_projection",
        "field": "email",
    }
    assert users.projections.lookup_calls == [("skriptoteket_standalone", CONTEXT_SUBJECT)]


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
    assert users.projections.lookup_calls == []


@pytest.mark.asyncio
async def test_app_dependency_accepts_signed_context_for_read_and_write_without_local_session(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles)
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


@pytest.mark.asyncio
async def test_app_dependency_accepts_standalone_realm_context_without_org_or_tenant(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles)
    headers = build_headers(
        private_key=private_key,
        now_ts=int(clock.now().timestamp()),
        payload_removed_fields=("org_id", "tenant_id", "active_context"),
        payload_overrides={
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "realm_subject_id": CONTEXT_SUBJECT,
            "linked_identity_ids": {"skriptoteket_standalone": CONTEXT_SUBJECT},
        },
    )

    response = await client.get("/api/v1/profile/app-continuation", headers=headers)

    assert response.status_code == 200
    assert response.json()["local_user"]["id"] == str(user.id)
    assert users.projections.lookup_calls == [("skriptoteket_standalone", CONTEXT_SUBJECT)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload_overrides", "payload_removed_fields", "expected_field"),
    [
        pytest.param(
            {"active_app": "huledu"},
            (),
            "active_app",
            id="wrong-active-app",
        ),
        pytest.param(
            {},
            ("active_app",),
            "active_app",
            id="missing-active-app",
        ),
        pytest.param(
            {"active_product_identity_realm": "unknown_realm"},
            (),
            "active_product_identity_realm",
            id="unsupported-realm",
        ),
        pytest.param(
            {},
            ("active_product_identity_realm",),
            "active_product_identity_realm",
            id="missing-realm",
        ),
        pytest.param(
            {},
            ("realm_subject_id",),
            "realm_subject_id",
            id="missing-realm-subject",
        ),
    ],
)
async def test_profile_app_continuation_requires_skriptoteket_product_context(
    payload_overrides: dict[str, JsonValue],
    payload_removed_fields: tuple[str, ...],
    expected_field: str,
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    users.user = huleedu_user()
    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
            payload_overrides=payload_overrides,
            payload_removed_fields=payload_removed_fields,
        ),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert response.json()["error"]["details"] == {
        "reason": "invalid_huleedu_product_context",
        "field": expected_field,
    }
    assert users.projections.lookup_calls == []


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
            "blank_org_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"org_id": " "},
            ),
            id="blank-org-id",
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
            "blank_active_app",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"active_app": " "},
            ),
            id="blank-active-app",
        ),
        pytest.param(
            "blank_realm_subject_id",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"realm_subject_id": " "},
            ),
            id="blank-realm-subject-id",
        ),
        pytest.param(
            "blank_linked_identity",
            lambda private_key, now_ts: build_headers(
                private_key=private_key,
                now_ts=now_ts,
                payload_overrides={"linked_identity_ids": {"skriptoteket_standalone": " "}},
            ),
            id="blank-linked-identity",
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
