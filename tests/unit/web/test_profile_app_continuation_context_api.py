"""Profile continuation auth-context rejection tests.

Purpose:
    Verify that HuleEdu context and product-realm validation failures stay
    fail-closed before local projection lookup or provisioning.

Relationships:
    - Shares the FastAPI/Dishka route fixture with the main continuation tests.
    - Covers invalid context syntax, trust, lifetime, and product-context shape.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from skriptoteket.domain.errors import ErrorCode
from skriptoteket.domain.identity.internal_identity_context import (
    INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
    INTERNAL_IDENTITY_KEY_ID_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_PREFIX,
)
from tests.fixtures.profile_app_continuation_api_app import InvalidHeadersBuilder
from tests.fixtures.profile_app_continuation_support import (
    AuthOutcomeRecorderStub,
    ClockStub,
    JsonValue,
    UserRepositoryStub,
    b64url_encode,
    build_headers,
    huleedu_user,
)

pytest_plugins = ("tests.fixtures.profile_app_continuation_api_app",)


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


@pytest.mark.asyncio
async def test_profile_app_continuation_records_signed_context_rejection(
    client: httpx.AsyncClient,
    auth_outcomes: AuthOutcomeRecorderStub,
) -> None:
    correlation_id = "d2481ff5-d4c7-43c3-81fc-b20f728ba8a4"

    response = await client.get(
        "/api/v1/profile/app-continuation",
        headers={"X-Correlation-ID": correlation_id},
    )

    assert response.status_code == 401
    assert response.json()["error"]["details"] == {
        "reason": "missing_internal_identity_headers",
    }
    assert auth_outcomes.context_verifications == [
        ("rejected", "missing_internal_identity_headers", UUID(correlation_id))
    ]


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
