"""Profile continuation app-dependency tests.

Purpose:
    Verify protected API dependencies can use the signed HuleEdu context while
    rejecting stale app-local browser session assumptions.

Relationships:
    - Shares the FastAPI/Dishka route fixture with profile continuation tests.
    - Covers the `require_app_user_api` dependency through read/write routes.
"""

from __future__ import annotations

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from skriptoteket.domain.errors import ErrorCode
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
