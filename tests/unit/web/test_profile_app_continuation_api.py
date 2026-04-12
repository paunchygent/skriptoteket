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

from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from skriptoteket.domain.errors import ErrorCode
from tests.fixtures.identity_fixtures import make_user_profile
from tests.fixtures.profile_app_continuation_support import (
    CONTEXT_SUBJECT,
    ClockStub,
    ProfileRepositoryStub,
    UserRepositoryStub,
    build_headers,
    huleedu_user,
    seed_huleedu_projection,
)

pytest_plugins = ("tests.fixtures.profile_app_continuation_api_app",)


@pytest.mark.asyncio
async def test_profile_app_continuation_accepts_valid_huleedu_context_without_local_session_cookie(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    correlation_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
    user = seed_huleedu_projection(users=users, profiles=profiles)
    profile = make_user_profile(
        user_id=user.id,
        allow_remote_fallback=True,
        inline_completion_provider="external",
    )
    profiles.result = profile

    headers = build_headers(
        private_key=private_key,
        now_ts=int(clock.now().timestamp()),
    )
    headers["X-Correlation-ID"] = str(correlation_id)
    response = await client.get("/api/v1/profile/app-continuation", headers=headers)

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
    assert users.projection_events.created[-1].correlation_id == correlation_id


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
    correlation_id = UUID("4957ebe7-d3ec-4e8c-b103-fd7baa45321e")
    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers={
            **build_headers(
                private_key=private_key,
                now_ts=int(clock.now().timestamp()),
            ),
            "X-Correlation-ID": str(correlation_id),
        },
    )

    assert response.status_code == 200
    assert response.json()["local_user"]["role"] == "user"
    assert response.json()["local_user"]["auth_provider"] == "huleedu"
    assert response.json()["local_user"]["email"] == "teacher@example.test"
    assert response.json()["profile"]["display_name"] == "Local Teacher"
    assert users.projections.created[0].realm_subject_id == CONTEXT_SUBJECT
    assert profiles.created is not None
    assert users.projection_events.created[-1].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_profile_app_continuation_fails_closed_without_signed_provisioning_claims(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    correlation_id = UUID("ab91e1c1-36eb-4936-a7da-790713808722")
    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers={
            **build_headers(
                private_key=private_key,
                now_ts=int(clock.now().timestamp()),
                payload_removed_fields=("email",),
            ),
            "X-Correlation-ID": str(correlation_id),
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert response.json()["error"]["details"] == {
        "reason": "missing_huleedu_app_projection",
        "field": "email",
    }
    assert users.projections.lookup_calls == [("skriptoteket_standalone", CONTEXT_SUBJECT)]
    assert users.projection_events.created[-1].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_profile_app_continuation_duplicate_email_records_correlation(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    correlation_id = UUID("09bfdb46-b59d-48f1-a9d4-a5c54ade4bb6")
    users.user = huleedu_user()

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers={
            **build_headers(
                private_key=private_key,
                now_ts=int(clock.now().timestamp()),
                payload_overrides={"realm_subject_id": "new-huleedu-subject"},
            ),
            "X-Correlation-ID": str(correlation_id),
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["details"] == {
        "reason": "identity_linking_required",
        "field": "email",
    }
    assert users.projection_events.created[-1].reason_code == "identity_linking_required"
    assert users.projection_events.created[-1].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_profile_app_continuation_invalid_product_context_records_correlation(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    correlation_id = UUID("fe187b45-68f1-42b5-9621-f81d85316c65")
    users.user = huleedu_user()

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers={
            **build_headers(
                private_key=private_key,
                now_ts=int(clock.now().timestamp()),
                payload_overrides={"active_product_identity_realm": "unknown_realm"},
            ),
            "X-Correlation-ID": str(correlation_id),
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["details"] == {
        "reason": "invalid_huleedu_product_context",
        "field": "active_product_identity_realm",
    }
    assert users.projection_events.created[-1].reason_code == (
        "invalid_active_product_identity_realm"
    )
    assert users.projection_events.created[-1].correlation_id == correlation_id
