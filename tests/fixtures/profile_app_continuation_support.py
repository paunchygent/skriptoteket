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
from typing import Literal, cast
from uuid import UUID, uuid4

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
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserAuth, UserProfile
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    ProductIdentityRealm,
)
from skriptoteket.infrastructure.security.huleedu_internal_identity import (
    HuleEduInternalIdentityVerifier,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user, make_user_profile

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]

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


class IdGeneratorStub:
    def new_uuid(self) -> UUID:
        return uuid4()


class IdentityProjectionRepositoryStub:
    def __init__(self) -> None:
        self.result: IdentityProjection | None = None
        self.lookup_calls: list[tuple[str, str]] = []
        self.realm_locks: list[tuple[str, str]] = []
        self.email_locks: list[str] = []
        self.created: list[IdentityProjection] = []

    async def lock_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> None:
        self.realm_locks.append((product_identity_realm, realm_subject_id))

    async def lock_email(self, *, email: str) -> None:
        self.email_locks.append(email)

    async def get_by_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> IdentityProjection | None:
        self.lookup_calls.append((product_identity_realm, realm_subject_id))
        if (
            self.result is None
            or self.result.product_identity_realm.value != product_identity_realm
            or self.result.realm_subject_id != realm_subject_id
        ):
            return None
        return self.result

    async def create(self, *, projection: IdentityProjection) -> IdentityProjection:
        self.created.append(projection)
        self.result = projection
        return projection


class IdentityProjectionEventRepositoryStub:
    def __init__(self) -> None:
        self.created: list[IdentityProjectionEvent] = []

    async def create(self, *, event: IdentityProjectionEvent) -> IdentityProjectionEvent:
        self.created.append(event)
        return event


class UserRepositoryStub:
    def __init__(self) -> None:
        self.user: User | None = None
        self.projections = IdentityProjectionRepositoryStub()
        self.projection_events = IdentityProjectionEventRepositoryStub()
        self.created: list[User] = []

    async def get_by_id(self, user_id: UUID) -> User | None:
        if self.user is None or self.user.id != user_id:
            return None
        return self.user

    async def get_auth_by_email(self, email: str) -> UserAuth | None:
        if self.user is not None and self.user.email == email:
            return UserAuth(user=self.user, password_hash=None)
        return None

    async def create(self, *, user: User, password_hash: str | None) -> User:
        self.created.append(user)
        self.user = user
        return user

    async def update(self, *, user: User) -> User:
        raise NotImplementedError

    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, updated_at: datetime
    ) -> None:
        raise NotImplementedError

    async def list_users(self, *, limit: int, offset: int) -> list[User]:
        raise NotImplementedError

    async def count_all(self) -> int:
        raise NotImplementedError

    async def count_active_by_role(self) -> dict[Role, int]:
        raise NotImplementedError


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

    async def update(self, *, profile: UserProfile) -> UserProfile:
        self.result = profile
        return profile


class ProfileContinuationApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        projections: IdentityProjectionRepositoryProtocol | None = None,
        projection_events: IdentityProjectionEventRepositoryProtocol | None = None,
        id_generator: IdGeneratorProtocol | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._users = users
        self._profiles = profiles
        stub_users = cast(UserRepositoryStub, users)
        self._projections = projections or stub_users.projections
        self._projection_events = projection_events or stub_users.projection_events
        self._id_generator = id_generator or IdGeneratorStub()
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
        return self._users

    @provide(scope=Scope.REQUEST)
    def profiles(self) -> ProfileRepositoryProtocol:
        return self._profiles

    @provide(scope=Scope.REQUEST)
    def projections(self) -> IdentityProjectionRepositoryProtocol:
        return self._projections

    @provide(scope=Scope.REQUEST)
    def projection_events(self) -> IdentityProjectionEventRepositoryProtocol:
        return self._projection_events

    @provide(scope=Scope.REQUEST)
    def uow(self) -> UnitOfWorkProtocol:
        return self._uow

    @provide(scope=Scope.APP)
    def id_generator(self) -> IdGeneratorProtocol:
        return self._id_generator

    @provide(scope=Scope.REQUEST)
    def huleedu_app_projection_resolver(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        projections: IdentityProjectionRepositoryProtocol,
        projection_events: IdentityProjectionEventRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> HuleEduAppProjectionResolverProtocol:
        return HuleEduAppProjectionResolver(
            uow=uow,
            users=users,
            profiles=profiles,
            projections=projections,
            projection_events=projection_events,
            clock=clock,
            id_generator=id_generator,
        )


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _encode_payload(payload: Mapping[str, JsonValue]) -> str:
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


def _build_context_payload(*, now_ts: int, **overrides: JsonValue) -> JsonObject:
    payload: JsonObject = {
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
        "active_app": "skriptoteket",
        "active_product_identity_realm": "skriptoteket_standalone",
        "realm_subject_id": CONTEXT_SUBJECT,
        "linked_identity_ids": {"skriptoteket_standalone": CONTEXT_SUBJECT},
        "email": "teacher@example.test",
        "email_verified": True,
        "given_name": "Local",
        "family_name": "Teacher",
        "display_name": "Local Teacher",
        "locale": "sv-SE",
    }
    payload.update(overrides)
    return payload


def build_headers(
    *,
    private_key: rsa.RSAPrivateKey,
    now_ts: int,
    payload_overrides: Mapping[str, JsonValue] | None = None,
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
            "email_verified": True,
        }
    )


def signed_huleedu_headers(
    *,
    private_key: rsa.RSAPrivateKey,
    clock: ClockProtocol,
    subject: str = CONTEXT_SUBJECT,
    payload_overrides: Mapping[str, JsonValue] | None = None,
) -> dict[str, str]:
    """Build a signed gateway context for browser API route tests."""

    overrides: JsonObject = {
        "sub": subject,
        "realm_subject_id": subject,
        "linked_identity_ids": {"skriptoteket_standalone": subject},
    }
    overrides.update(dict(payload_overrides or {}))
    return build_headers(
        private_key=private_key,
        now_ts=int(clock.now().timestamp()),
        payload_overrides=overrides,
    )


def seed_huleedu_projection(
    *,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    role: Role = Role.CONTRIBUTOR,
    now: datetime | None = None,
    subject: str = CONTEXT_SUBJECT,
    email: str = "teacher@example.test",
    allow_remote_fallback: bool | None = None,
    inline_completion_provider: Literal["local", "external"] | None = None,
) -> User:
    """Seed the local projection expected after HuleEdu gateway verification."""

    user = huleedu_user(user=make_user(role=role, email=email))
    users.user = user
    now_value = now or user.created_at
    users.projections.result = IdentityProjection(
        id=uuid4(),
        user_id=user.id,
        product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
        realm_subject_id=subject,
        created_at=now_value,
        updated_at=now_value,
    )
    profiles.result = make_user_profile(
        user_id=user.id,
        allow_remote_fallback=allow_remote_fallback,
        inline_completion_provider=inline_completion_provider,
        now=now,
    )
    return user
