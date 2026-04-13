"""HuleEdu internal identity diagnostic probe route tests.

Purpose:
    Verify the hidden consumer probe used by HuleEdu provider live apply
    returns sanitized signed-context claim proof without creating local users or
    projections.

Relationships:
    - Exercises `src.skriptoteket.web.api.v1.diagnostics` through FastAPI.
    - Reuses the real internal identity verifier fixture shared with
      app-continuation tests.
"""

from __future__ import annotations

import json

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
)

pytest_plugins = ("tests.fixtures.profile_app_continuation_api_app",)


PROBE_PATH = "/api/v1/diagnostics/huleedu-internal-identity"


@pytest.mark.asyncio
async def test_probe_returns_sanitized_decoded_context_without_projection_side_effects(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    response = await client.get(
        PROBE_PATH,
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "app": "skriptoteket",
        "product_identity_realm": "skriptoteket_standalone",
        "claims": {
            "context_version": 1,
            "issuer": "api_gateway_service",
            "audience": "skriptoteket",
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "realm_subject_id_present": True,
            "subject_claim_present": True,
            "subject_matches_realm_subject": True,
            "linked_identity_realm_present": True,
            "linked_identity_matches_realm_subject": True,
            "email_present": True,
            "email_verified": True,
            "org_id_present": True,
            "tenant_id_present": True,
            "source_app": "huleedu-browser",
            "roles": ["teacher"],
            "grants": ["tools:run"],
            "feature_flags": ["inline-completion"],
            "active_context_keys": ["org_id", "tenant_id"],
            "policy_version": "2026-04-09",
            "issued_at": int(clock.now().timestamp()),
            "expires_at": int(clock.now().timestamp()) + 60,
        },
    }

    serialized_payload = json.dumps(payload, sort_keys=True)
    assert CONTEXT_SUBJECT not in serialized_payload
    assert "huleedu-session" not in serialized_payload
    assert "ctx-test-1" not in serialized_payload
    assert "teacher@example.test" not in serialized_payload
    assert "X-Huledu-Identity" not in serialized_payload
    assert users.created == []
    assert users.projections.lookup_calls == []
    assert users.projections.created == []
    assert users.projection_events.created == []
    assert profiles.created is None
    assert profiles.get_by_user_id_calls == []


@pytest.mark.asyncio
async def test_probe_rejects_invalid_product_context_before_projection_lookup(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
) -> None:
    response = await client.get(
        PROBE_PATH,
        headers=build_headers(
            private_key=private_key,
            now_ts=int(clock.now().timestamp()),
            payload_overrides={"active_app": "huleedu"},
        ),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert response.json()["error"]["details"] == {
        "reason": "invalid_huleedu_product_context",
        "field": "active_app",
    }
    assert users.projections.lookup_calls == []
    assert users.created == []
    assert users.projections.created == []
    assert users.projection_events.created == []
