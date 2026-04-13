"""Unit tests for applying the bootstrap projection role matrix.

Purpose:
    Prove validated HuleEdu export rows create/update local users,
    `identity_projections`, and `User.role` without email-only inference.

Relationships:
    - Exercises `HuleEduSubjectExportConsumer` through protocol-shaped fakes.
    - Complements schema validation coverage in
      `test_bootstrap_subject_export_schema.py`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.identity.huleedu_subject_export_consumer import (
    HuleEduSubjectExportConsumer,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    SUBJECT_EXPORT_SCHEMA_VERSION,
    parse_huleedu_subject_export,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserAuth
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    IdentityProjectionEventType,
    ProductIdentityRealm,
)


class FakeUow:
    def __init__(self) -> None:
        self.entries = 0

    async def __aenter__(self) -> "FakeUow":
        self.entries += 1
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def __init__(self) -> None:
        self.generated: list[UUID] = []

    def new_uuid(self) -> UUID:
        value = uuid4()
        self.generated.append(value)
        return value


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.password_hashes: dict[UUID, str | None] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def get_auth_by_email(self, email: str) -> UserAuth | None:
        for user_id, user in self.users.items():
            if user.email == email:
                return UserAuth(user=user, password_hash=self.password_hashes[user_id])
        return None

    async def create(self, *, user: User, password_hash: str | None) -> User:
        self.users[user.id] = user
        self.password_hashes[user.id] = password_hash
        return user

    async def create_if_email_available(
        self, *, user: User, password_hash: str | None
    ) -> User | None:
        if await self.get_auth_by_email(user.email) is not None:
            return None
        return await self.create(user=user, password_hash=password_hash)

    async def update(self, *, user: User) -> User:
        self.users[user.id] = user
        return user

    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, updated_at: datetime
    ) -> None:
        self.password_hashes[user_id] = password_hash

    async def list_users(self, *, limit: int, offset: int) -> list[User]:
        return list(self.users.values())[offset : offset + limit]

    async def count_all(self) -> int:
        return len(self.users)

    async def count_active_by_role(self) -> dict[Role, int]:
        counts: dict[Role, int] = {}
        for user in self.users.values():
            if user.is_active:
                counts[user.role] = counts.get(user.role, 0) + 1
        return counts


class FakeProjectionRepository:
    def __init__(self) -> None:
        self.projections: dict[tuple[str, str], IdentityProjection] = {}
        self.realm_locks: list[tuple[str, str]] = []
        self.email_locks: list[str] = []

    async def lock_realm_subject(
        self, *, product_identity_realm: str, realm_subject_id: str
    ) -> None:
        self.realm_locks.append((product_identity_realm, realm_subject_id))

    async def lock_email(self, *, email: str) -> None:
        self.email_locks.append(email)

    async def get_by_realm_subject(
        self, *, product_identity_realm: str, realm_subject_id: str
    ) -> IdentityProjection | None:
        return self.projections.get((product_identity_realm, realm_subject_id))

    async def create(self, *, projection: IdentityProjection) -> IdentityProjection:
        self.projections[(projection.product_identity_realm.value, projection.realm_subject_id)] = (
            projection
        )
        return projection

    async def create_if_realm_subject_absent(
        self, *, projection: IdentityProjection
    ) -> IdentityProjection | None:
        key = (projection.product_identity_realm.value, projection.realm_subject_id)
        if key in self.projections:
            return None
        self.projections[key] = projection
        return projection


class FakeProjectionEventRepository:
    def __init__(self) -> None:
        self.events: list[IdentityProjectionEvent] = []

    async def create(self, *, event: IdentityProjectionEvent) -> IdentityProjectionEvent:
        self.events.append(event)
        return event


def _record(
    *,
    stable_account_key: str,
    role_hint: str,
    email: str,
    subject: str,
) -> dict[str, object]:
    return {
        "stable_account_key": stable_account_key,
        "active_app": "skriptoteket",
        "active_product_identity_realm": "skriptoteket_standalone",
        "realm_subject_id": subject,
        "email": email,
        "email_verified": True,
        "skriptoteket_role_hint": role_hint,
        "huleedu_subject_id": f"huleedu-{subject}",
    }


def _payload(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "status": "ok",
        "errors": [],
        "export": {
            "schema_version": SUBJECT_EXPORT_SCHEMA_VERSION,
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "accounts": records,
        },
    }


def _proof_payload() -> dict[str, object]:
    return _payload(
        [
            _record(
                stable_account_key="skriptoteket-proof-user",
                role_hint="user",
                email="skriptoteket-proof-user@hule.education",
                subject="realm-user",
            ),
            _record(
                stable_account_key="skriptoteket-proof-admin",
                role_hint="admin",
                email="skriptoteket-proof-admin@hule.education",
                subject="realm-admin",
            ),
            _record(
                stable_account_key="skriptoteket-proof-superuser",
                role_hint="superuser",
                email="skriptoteket-proof-superuser@hule.education",
                subject="realm-superuser",
            ),
        ]
    )


def _user(*, email: str, role: Role, now: datetime, auth_provider: AuthProvider) -> User:
    return User(
        id=uuid4(),
        email=email,
        role=role,
        auth_provider=auth_provider,
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )


def _projection(*, user_id: UUID, subject: str, now: datetime) -> IdentityProjection:
    return IdentityProjection(
        id=uuid4(),
        user_id=user_id,
        product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
        realm_subject_id=subject,
        created_at=now,
        updated_at=now,
    )


def _consumer(
    *,
    users: FakeUserRepository,
    projections: FakeProjectionRepository,
    events: FakeProjectionEventRepository,
    now: datetime,
) -> HuleEduSubjectExportConsumer:
    return HuleEduSubjectExportConsumer(
        uow=FakeUow(),
        users=users,
        projections=projections,
        projection_events=events,
        clock=FakeClock(now),
        id_generator=FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_apply_creates_local_huleedu_users_roles_and_projections(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    consumer = _consumer(users=users, projections=projections, events=events, now=now)

    result = await consumer.consume(
        export=parse_huleedu_subject_export(_proof_payload()),
        dry_run=False,
    )

    assert result.created_users == 3
    assert result.created_projections == 3
    assert result.would_create_users == 0
    assert result.would_create_projections == 0
    assert result.would_update_users == 0
    assert {user.email: user.role for user in users.users.values()} == {
        "skriptoteket-proof-user@hule.education": Role.USER,
        "skriptoteket-proof-admin@hule.education": Role.ADMIN,
        "skriptoteket-proof-superuser@hule.education": Role.SUPERUSER,
    }
    assert {user.auth_provider for user in users.users.values()} == {AuthProvider.HULEEDU}
    assert set(users.password_hashes.values()) == {None}
    assert len(projections.projections) == 3
    assert [event.reason_code for event in events.events] == [
        "subject_export_projection_created",
        "subject_export_projection_created",
        "subject_export_projection_created",
    ]


@pytest.mark.asyncio
async def test_rerun_is_idempotent_and_does_not_duplicate_rows(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    consumer = _consumer(users=users, projections=projections, events=events, now=now)
    export = parse_huleedu_subject_export(_proof_payload())

    await consumer.consume(export=export, dry_run=False)
    result = await consumer.consume(export=export, dry_run=False)

    assert result.unchanged == 3
    assert result.would_create_users == 0
    assert result.would_create_projections == 0
    assert result.would_update_users == 0
    assert len(users.users) == 3
    assert len(projections.projections) == 3
    assert [event.reason_code for event in events.events[-3:]] == [
        "subject_export_projection_unchanged",
        "subject_export_projection_unchanged",
        "subject_export_projection_unchanged",
    ]


@pytest.mark.asyncio
async def test_existing_projection_promotes_but_never_downgrades_role(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    admin = await users.create(
        user=_user(
            email="skriptoteket-proof-admin@hule.education",
            role=Role.USER,
            now=now,
            auth_provider=AuthProvider.HULEEDU,
        ),
        password_hash=None,
    )
    proof_user = await users.create(
        user=_user(
            email="skriptoteket-proof-user@hule.education",
            role=Role.SUPERUSER,
            now=now,
            auth_provider=AuthProvider.HULEEDU,
        ),
        password_hash=None,
    )
    await projections.create(
        projection=_projection(user_id=admin.id, subject="realm-admin", now=now)
    )
    await projections.create(
        projection=_projection(user_id=proof_user.id, subject="realm-user", now=now)
    )
    consumer = _consumer(users=users, projections=projections, events=events, now=now)
    export = parse_huleedu_subject_export(
        _payload(
            [
                _record(
                    stable_account_key="skriptoteket-proof-admin",
                    role_hint="admin",
                    email="skriptoteket-proof-admin@hule.education",
                    subject="realm-admin",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-user",
                    role_hint="user",
                    email="skriptoteket-proof-user@hule.education",
                    subject="realm-user",
                ),
            ]
        )
    )

    result = await consumer.consume(export=export, dry_run=False)

    assert result.updated_users == 1
    assert result.would_create_users == 0
    assert result.would_create_projections == 0
    assert result.would_update_users == 0
    assert users.users[admin.id].role is Role.ADMIN
    assert users.users[proof_user.id].role is Role.SUPERUSER


@pytest.mark.asyncio
async def test_existing_email_without_projection_fails_closed(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    await users.create(
        user=_user(
            email="skriptoteket-proof-user@hule.education",
            role=Role.USER,
            now=now,
            auth_provider=AuthProvider.LOCAL,
        ),
        password_hash="local-password-hash",
    )
    consumer = _consumer(users=users, projections=projections, events=events, now=now)

    with pytest.raises(DomainError) as exc_info:
        await consumer.consume(export=parse_huleedu_subject_export(_proof_payload()), dry_run=False)

    assert exc_info.value.code == ErrorCode.CONFLICT
    assert exc_info.value.details == {
        "reason": "identity_linking_required",
        "stable_account_key": "skriptoteket-proof-user",
        "field": "email",
    }
    assert len(users.users) == 1
    assert projections.projections == {}
    assert [(event.event_type, event.reason_code) for event in events.events] == [
        (
            IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED,
            "identity_linking_required",
        )
    ]


@pytest.mark.asyncio
async def test_dry_run_reports_plans_without_writes(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    consumer = _consumer(users=users, projections=projections, events=events, now=now)

    result = await consumer.consume(
        export=parse_huleedu_subject_export(_proof_payload()),
        dry_run=True,
    )

    assert [account.action for account in result.account_results] == [
        "would_create",
        "would_create",
        "would_create",
    ]
    assert result.created_users == 0
    assert result.created_projections == 0
    assert result.updated_users == 0
    assert result.would_create_users == 3
    assert result.would_create_projections == 3
    assert result.would_update_users == 0
    assert result.unchanged == 0
    assert users.users == {}
    assert projections.projections == {}
    assert events.events == []


@pytest.mark.asyncio
async def test_dry_run_reports_would_update_without_writing(now: datetime) -> None:
    users = FakeUserRepository()
    projections = FakeProjectionRepository()
    events = FakeProjectionEventRepository()
    admin = await users.create(
        user=_user(
            email="skriptoteket-proof-admin@hule.education",
            role=Role.USER,
            now=now,
            auth_provider=AuthProvider.HULEEDU,
        ),
        password_hash=None,
    )
    await projections.create(
        projection=_projection(user_id=admin.id, subject="realm-admin", now=now)
    )
    consumer = _consumer(users=users, projections=projections, events=events, now=now)
    export = parse_huleedu_subject_export(
        _payload(
            [
                _record(
                    stable_account_key="skriptoteket-proof-admin",
                    role_hint="admin",
                    email="skriptoteket-proof-admin@hule.education",
                    subject="realm-admin",
                )
            ]
        )
    )

    result = await consumer.consume(export=export, dry_run=True)

    assert [account.action for account in result.account_results] == ["would_update"]
    assert result.created_users == 0
    assert result.created_projections == 0
    assert result.updated_users == 0
    assert result.would_create_users == 0
    assert result.would_create_projections == 0
    assert result.would_update_users == 1
    assert result.unchanged == 0
    assert users.users[admin.id].role is Role.USER
    assert events.events == []
