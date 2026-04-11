"""Test support for profile app-continuation API checks.

Purpose:
    Provide signing helpers and protocol stubs for tests that exercise the
    HuleEdu internal identity context plus Skriptoteket-local projection path.

Relationships:
    - Shared by unit tests and the PR-0255 Playwright proof script.
    - Builds the same Dishka provider graph used by the route-level tests.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from dishka import Provider, Scope, provide

from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppProjectionResolver
from skriptoteket.config import Settings
from skriptoteket.domain.identity.internal_identity_context import (
    INTERNAL_IDENTITY_CONTEXT_HEADER,
    INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
    INTERNAL_IDENTITY_KEY_ID_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_PREFIX,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile
from skriptoteket.infrastructure.security.huleedu_internal_identity import (
    HuleEduInternalIdentityVerifier,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user

CONTEXT_SUBJECT = "huleedu-teacher-subject"
KEY_ID = "gateway-identity-rs256-v1"


class UnitOfWorkStub:
    async def __aenter__(self) -> "UnitOfWorkStub":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        return None


class ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class UserRepositoryStub:
    def __init__(self) -> None:
        self.user: User | None = None
        self.lookup_calls: list[tuple[AuthProvider, str]] = []

    async def get_by_auth_provider_external_id(
        self,
        *,
        auth_provider: AuthProvider,
        external_id: str,
    ) -> User | None:
        self.lookup_calls.append((auth_provider, external_id))
        if (
            self.user is None
            or self.user.auth_provider is not auth_provider
            or self.user.external_id != external_id
        ):
            return None
        return self.user


class ProfileRepositoryStub:
    def __init__(self) -> None:
        self.result: UserProfile | None = None
        self.created: UserProfile | None = None
        self.get_by_user_id_calls: list[UUID] = []

    async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None:
        self.get_by_user_id_calls.append(user_id)
        return self.result

    async def create(self, *, profile: UserProfile) -> UserProfile:
        self.created = profile
        self.result = profile
        return profile


class ProfileContinuationApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        users: object,
        profiles: object,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._users = users
        self._profiles = profiles
        self._uow = UnitOfWorkStub()

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.APP)
    def huleedu_internal_identity_verifier(self) -> HuleEduInternalIdentityVerifierProtocol:
        return HuleEduInternalIdentityVerifier(self._settings)

    @provide(scope=Scope.REQUEST)
    def users(self) -> UserRepositoryProtocol:
        return cast(UserRepositoryProtocol, self._users)

    @provide(scope=Scope.REQUEST)
    def profiles(self) -> ProfileRepositoryProtocol:
        return cast(ProfileRepositoryProtocol, self._profiles)

    @provide(scope=Scope.REQUEST)
    def uow(self) -> UnitOfWorkProtocol:
        return self._uow

    @provide(scope=Scope.REQUEST)
    def huleedu_app_projection_resolver(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> HuleEduAppProjectionResolverProtocol:
        return HuleEduAppProjectionResolver(
            uow=uow,
            users=users,
            profiles=profiles,
            clock=clock,
        )


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _encode_payload(payload: Mapping[str, Any]) -> str:
    raw_payload = json.dumps(
        dict(payload),
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return b64url_encode(raw_payload)


def _sign_context(*, encoded_context: str, private_key: rsa.RSAPrivateKey) -> str:
    signature = private_key.sign(
        encoded_context.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return b64url_encode(signature)


def _build_context_payload(*, now_ts: int, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "context_version": 1,
        "iss": "api_gateway_service",
        "aud": "skriptoteket",
        "sub": CONTEXT_SUBJECT,
        "session_id": "huleedu-session",
        "org_id": "org-1",
        "tenant_id": "tenant-1",
        "roles": ["teacher"],
        "grants": ["tools:run"],
        "policy_version": "2026-04-09",
        "iat": now_ts,
        "exp": now_ts + 60,
        "jti": "ctx-test-1",
        "active_context": {"org_id": "org-1", "tenant_id": "tenant-1"},
        "feature_flags": ["inline-completion"],
        "source_app": "huleedu-browser",
    }
    payload.update(overrides)
    return payload


def build_headers(
    *,
    private_key: rsa.RSAPrivateKey,
    now_ts: int,
    payload_overrides: Mapping[str, Any] | None = None,
    payload_removed_fields: Iterable[str] = (),
    header_overrides: Mapping[str, str] | None = None,
    encoded_context: str | None = None,
) -> dict[str, str]:
    payload = _build_context_payload(now_ts=now_ts, **dict(payload_overrides or {}))
    for field_name in payload_removed_fields:
        payload.pop(field_name, None)
    resolved_context = encoded_context or _encode_payload(payload)
    signature = _sign_context(encoded_context=resolved_context, private_key=private_key)
    headers = {
        INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER: "1",
        INTERNAL_IDENTITY_CONTEXT_HEADER: resolved_context,
        INTERNAL_IDENTITY_KEY_ID_HEADER: KEY_ID,
        INTERNAL_IDENTITY_SIGNATURE_HEADER: f"{INTERNAL_IDENTITY_SIGNATURE_PREFIX}{signature}",
    }
    headers.update(header_overrides or {})
    return headers


def huleedu_user(*, user: User | None = None) -> User:
    base_user = user or make_user(role=Role.CONTRIBUTOR, email="teacher@example.test")
    return base_user.model_copy(
        update={
            "auth_provider": AuthProvider.HULEEDU,
            "external_id": CONTEXT_SUBJECT,
            "email_verified": True,
        }
    )
