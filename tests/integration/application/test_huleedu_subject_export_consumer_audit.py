"""Integration tests for HuleEdu subject export blocked-mapping audit.

Purpose:
    Prove blocked subject export applies leave no partial identity mutations
    while retaining a durable local projection audit event.

Relationships:
    - Exercises `HuleEduSubjectExportConsumer` with real SQLAlchemy UoW and
      identity repositories.
    - Complements unit coverage for schema validation and role-matrix behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from skriptoteket.application.identity.huleedu_subject_export_consumer import (
    HuleEduSubjectExportConsumer,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    SUBJECT_EXPORT_SCHEMA_VERSION,
    parse_huleedu_subject_export,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.models.identity_projection import (
    IdentityProjectionEventModel,
    IdentityProjectionModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _provider_export() -> dict[str, object]:
    return {
        "status": "ok",
        "errors": [],
        "export": {
            "schema_version": SUBJECT_EXPORT_SCHEMA_VERSION,
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "accounts": [
                {
                    "stable_account_key": "skriptoteket-proof-user",
                    "active_app": "skriptoteket",
                    "active_product_identity_realm": "skriptoteket_standalone",
                    "realm_subject_id": "blocked-linking-subject",
                    "email": "blocked-linking@example.test",
                    "email_verified": True,
                    "skriptoteket_role_hint": "user",
                    "huleedu_subject_id": "diagnostic-blocked-linking-subject",
                }
            ],
        },
    }


def _consumer(session: AsyncSession) -> HuleEduSubjectExportConsumer:
    return HuleEduSubjectExportConsumer(
        uow=SQLAlchemyUnitOfWork(session),
        users=PostgreSQLUserRepository(session),
        projections=PostgreSQLIdentityProjectionRepository(session),
        projection_events=PostgreSQLIdentityProjectionEventRepository(session),
        clock=UTCClock(),
        id_generator=UUID4Generator(),
    )


async def _count_rows(
    session: AsyncSession, model: type[object], *criteria: ColumnElement[bool]
) -> int:
    stmt = select(func.count()).select_from(model)
    for criterion in criteria:
        stmt = stmt.where(criterion)
    return int(await session.scalar(stmt))


@pytest.mark.integration
async def test_blocked_email_linking_rolls_back_apply_and_commits_audit_event(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    del db_session
    now = datetime.now(timezone.utc)
    existing_user_id = uuid4()

    async with session_factory() as session:
        await PostgreSQLUserRepository(session).create(
            user=User(
                id=existing_user_id,
                email="blocked-linking@example.test",
                role=Role.USER,
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                email_verified=True,
                created_at=now,
                updated_at=now,
            ),
            password_hash="local-password-hash",
        )
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(DomainError) as exc_info:
            await _consumer(session).consume(
                export=parse_huleedu_subject_export(_provider_export()),
                dry_run=False,
            )

    assert exc_info.value.details == {
        "reason": "identity_linking_required",
        "stable_account_key": "skriptoteket-proof-user",
        "field": "email",
    }

    async with session_factory() as session:
        assert (
            await _count_rows(
                session,
                UserModel,
                UserModel.email == "blocked-linking@example.test",
            )
            == 1
        )
        assert (
            await _count_rows(
                session,
                IdentityProjectionModel,
                IdentityProjectionModel.realm_subject_id == "blocked-linking-subject",
            )
            == 0
        )
        result = await session.execute(
            select(
                IdentityProjectionEventModel.event_type,
                IdentityProjectionEventModel.reason_code,
                IdentityProjectionEventModel.product_identity_realm,
                IdentityProjectionEventModel.realm_subject_id,
            ).where(IdentityProjectionEventModel.realm_subject_id == "blocked-linking-subject")
        )

    assert result.all() == [
        (
            "duplicate_email_linking_required",
            "identity_linking_required",
            "skriptoteket_standalone",
            "blocked-linking-subject",
        )
    ]
