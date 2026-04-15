"""Integration tests for concurrent HuleEdu projection provisioning.

Purpose:
    Prove first-login provisioning remains idempotent under concurrent callback
    pressure and recovers from database-enforced uniqueness conflicts.

Relationships:
    - Exercises `HuleEduAppProjectionResolver` with real PostgreSQL
      repositories and `SQLAlchemyUnitOfWork`.
    - Complements route-level app-continuation tests by checking transaction
      behavior that stubs cannot prove.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.identity.huleedu_app_projection import (
    HuleEduAppProjectionResolver,
    HuleEduAppUserProjection,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile
from skriptoteket.domain.identity.projections import IdentityProjection, ProductIdentityRealm
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.models.identity_projection import (
    IdentityProjectionEventModel,
    IdentityProjectionModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.profile_repository import PostgreSQLProfileRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.observability.auth_outcomes import NoopAuthOutcomeRecorder

pytestmark = pytest.mark.asyncio(loop_scope="module")


class RacingProjectionRepository(PostgreSQLIdentityProjectionRepository):
    """Projection repository that injects one DB-backed race before insert."""

    def __init__(
        self,
        session: AsyncSession,
        on_create: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(session)
        self._on_create = on_create
        self._has_raced = False

    async def create_if_realm_subject_absent(
        self, *, projection: IdentityProjection
    ) -> IdentityProjection | None:
        if not self._has_raced:
            self._has_raced = True
            await self._on_create()
        return await super().create_if_realm_subject_absent(projection=projection)


def _context(
    *,
    subject: str,
    email: str,
    jti: str | None = None,
) -> InternalIdentityContextV1:
    return InternalIdentityContextV1(
        context_version=1,
        iss="api_gateway_service",
        aud="skriptoteket",
        sub=subject,
        session_id=f"session-{subject}",
        org_id="org-1",
        tenant_id="tenant-1",
        roles=["teacher"],
        grants=["tools:run"],
        policy_version="2026-04-12",
        iat=1_776_000_000,
        exp=1_776_000_060,
        jti=jti or f"ctx-{subject}",
        active_context={"org_id": "org-1", "tenant_id": "tenant-1"},
        feature_flags=[],
        source_app="huleedu-browser",
        active_app="skriptoteket",
        active_product_identity_realm="skriptoteket_standalone",
        realm_subject_id=subject,
        linked_identity_ids={"skriptoteket_standalone": subject},
        email=email,
        email_verified=True,
        given_name="Local",
        family_name="Teacher",
        display_name="Local Teacher",
        locale="sv-SE",
    )


def _resolver(
    session: AsyncSession,
    *,
    projections: PostgreSQLIdentityProjectionRepository | None = None,
) -> HuleEduAppProjectionResolver:
    return HuleEduAppProjectionResolver(
        uow=SQLAlchemyUnitOfWork(session),
        users=PostgreSQLUserRepository(session),
        profiles=PostgreSQLProfileRepository(session),
        projections=projections or PostgreSQLIdentityProjectionRepository(session),
        projection_events=PostgreSQLIdentityProjectionEventRepository(session),
        clock=UTCClock(),
        id_generator=UUID4Generator(),
        auth_outcomes=NoopAuthOutcomeRecorder(),
    )


async def _resolve_in_isolated_session(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    context: InternalIdentityContextV1,
    correlation_id: UUID,
    start_event: asyncio.Event,
) -> HuleEduAppUserProjection:
    await start_event.wait()
    async with session_factory() as session:
        return await _resolver(session).resolve(context=context, correlation_id=correlation_id)


async def _count_rows(session: AsyncSession, model: type[object], *criteria: object) -> int:
    stmt = select(func.count()).select_from(model)
    for criterion in criteria:
        stmt = stmt.where(criterion)  # type: ignore[arg-type]
    return int(await session.scalar(stmt))


async def _projection_events(
    session: AsyncSession, *, subject: str
) -> list[tuple[str, UUID | None]]:
    result = await session.execute(
        select(
            IdentityProjectionEventModel.reason_code, IdentityProjectionEventModel.correlation_id
        )
        .where(IdentityProjectionEventModel.realm_subject_id == subject)
        .order_by(IdentityProjectionEventModel.created_at)
    )
    return [(reason_code, correlation_id) for reason_code, correlation_id in result.all()]


@pytest.mark.integration
async def test_same_subject_concurrent_first_login_provisions_once(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    del db_session
    subject = "same-subject-race"
    email = "same-subject-race@example.test"
    context = _context(subject=subject, email=email)
    start_event = asyncio.Event()
    first_correlation_id = uuid4()
    second_correlation_id = uuid4()

    first = _resolve_in_isolated_session(
        session_factory=session_factory,
        context=context,
        correlation_id=first_correlation_id,
        start_event=start_event,
    )
    second = _resolve_in_isolated_session(
        session_factory=session_factory,
        context=context,
        correlation_id=second_correlation_id,
        start_event=start_event,
    )

    start_event.set()
    results = await asyncio.gather(first, second)

    assert results[0].user.id == results[1].user.id
    async with session_factory() as session:
        assert await _count_rows(session, UserModel, UserModel.email == email) == 1
        assert await _count_rows(session, UserProfileModel) == 1
        assert (
            await _count_rows(
                session,
                IdentityProjectionModel,
                IdentityProjectionModel.realm_subject_id == subject,
            )
            == 1
        )
        events = await _projection_events(session, subject=subject)

    assert {event[0] for event in events} == {"projection_provisioned", "projection_resolved"}
    assert {event[1] for event in events} == {first_correlation_id, second_correlation_id}


@pytest.mark.integration
async def test_same_email_concurrent_first_login_fails_one_identity_closed(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    del db_session
    email = "same-email-race@example.test"
    start_event = asyncio.Event()
    contexts = [
        _context(subject="same-email-race-a", email=email),
        _context(subject="same-email-race-b", email=email),
    ]
    correlations = [uuid4(), uuid4()]

    tasks = [
        _resolve_in_isolated_session(
            session_factory=session_factory,
            context=context,
            correlation_id=correlation_id,
            start_event=start_event,
        )
        for context, correlation_id in zip(contexts, correlations, strict=True)
    ]

    start_event.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [result for result in results if isinstance(result, HuleEduAppUserProjection)]
    failures = [result for result in results if isinstance(result, DomainError)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].details == {"reason": "identity_linking_required", "field": "email"}
    async with session_factory() as session:
        assert await _count_rows(session, UserModel, UserModel.email == email) == 1
        assert await _count_rows(session, UserProfileModel) == 1
        assert await _count_rows(session, IdentityProjectionModel) == 1
        event_count = await _count_rows(session, IdentityProjectionEventModel)

    assert event_count == 2


@pytest.mark.integration
async def test_projection_unique_conflict_recovers_and_rolls_back_orphan_user(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    del db_session
    subject = "projection-conflict-race"
    losing_email = "projection-conflict-losing@example.test"
    winning_email = "projection-conflict-winning@example.test"
    correlation_id = uuid4()
    context = _context(subject=subject, email=losing_email)

    async def insert_competing_projection() -> None:
        async with session_factory() as session:
            now = UTCClock().now()
            user = await PostgreSQLUserRepository(session).create_if_email_available(
                user=User(
                    id=uuid4(),
                    email=winning_email,
                    role=Role.USER,
                    auth_provider=AuthProvider.HULEEDU,
                    is_active=True,
                    email_verified=True,
                    created_at=now,
                    updated_at=now,
                ),
                password_hash=None,
            )
            if user is None:
                raise AssertionError("Expected competing user insert to succeed.")
            await PostgreSQLProfileRepository(session).create(
                profile=UserProfile(
                    user_id=user.id,
                    first_name="Winning",
                    last_name="Teacher",
                    display_name="Winning Teacher",
                    locale="sv-SE",
                    created_at=now,
                    updated_at=now,
                )
            )
            await PostgreSQLIdentityProjectionRepository(session).create_if_realm_subject_absent(
                projection=IdentityProjection(
                    id=uuid4(),
                    user_id=user.id,
                    product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
                    realm_subject_id=subject,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

    async with session_factory() as session:
        projections = RacingProjectionRepository(session, on_create=insert_competing_projection)
        result = await _resolver(session, projections=projections).resolve(
            context=context,
            correlation_id=correlation_id,
        )

    assert result.user.email == winning_email
    async with session_factory() as session:
        assert await _count_rows(session, UserModel, UserModel.email == losing_email) == 0
        assert await _count_rows(session, UserModel, UserModel.email == winning_email) == 1
        assert await _count_rows(session, UserProfileModel) == 1
        assert await _count_rows(session, IdentityProjectionModel) == 1
        events = await _projection_events(session, subject=subject)

    assert events == [("projection_conflict_recovered", correlation_id)]
