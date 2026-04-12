"""PostgreSQL repositories for realm-aware identity projections.

Purpose:
    Persist explicit product realm subject mappings and audit events used by
    HuleEdu-derived Skriptoteket app continuation and first-login provisioning.

Relationships:
    - Implements projection protocols from `skriptoteket.protocols.identity`.
    - Uses request-scoped SQLAlchemy sessions; Unit of Work owns transactions.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.projections import IdentityProjection, IdentityProjectionEvent
from skriptoteket.infrastructure.db.models.identity_projection import (
    IdentityProjectionEventModel,
    IdentityProjectionModel,
)
from skriptoteket.protocols.identity import (
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
)


class PostgreSQLIdentityProjectionRepository(IdentityProjectionRepositoryProtocol):
    """PostgreSQL repository for realm subject to local user projections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> None:
        await self._lock_key(f"realm:{product_identity_realm}:{realm_subject_id}")

    async def lock_email(self, *, email: str) -> None:
        await self._lock_key(f"email:{email}")

    async def get_by_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> IdentityProjection | None:
        stmt = select(IdentityProjectionModel).where(
            IdentityProjectionModel.product_identity_realm == product_identity_realm,
            IdentityProjectionModel.realm_subject_id == realm_subject_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return IdentityProjection.model_validate(model) if model else None

    async def create(self, *, projection: IdentityProjection) -> IdentityProjection:
        model = IdentityProjectionModel(
            id=projection.id,
            user_id=projection.user_id,
            product_identity_realm=projection.product_identity_realm.value,
            realm_subject_id=projection.realm_subject_id,
            created_at=projection.created_at,
            updated_at=projection.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return IdentityProjection.model_validate(model)

    async def create_if_realm_subject_absent(
        self, *, projection: IdentityProjection
    ) -> IdentityProjection | None:
        stmt = (
            pg_insert(IdentityProjectionModel)
            .values(
                id=projection.id,
                user_id=projection.user_id,
                product_identity_realm=projection.product_identity_realm.value,
                realm_subject_id=projection.realm_subject_id,
                created_at=projection.created_at,
                updated_at=projection.updated_at,
            )
            .on_conflict_do_nothing(constraint="uq_identity_projections_realm_subject")
            .returning(IdentityProjectionModel.id)
        )
        result = await self._session.execute(stmt)
        projection_id = result.scalar_one_or_none()
        return projection if projection_id is not None else None

    async def _lock_key(self, key: str) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": key},
        )


class PostgreSQLIdentityProjectionEventRepository(IdentityProjectionEventRepositoryProtocol):
    """PostgreSQL repository for identity projection audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, event: IdentityProjectionEvent) -> IdentityProjectionEvent:
        model = IdentityProjectionEventModel(
            id=event.id,
            event_type=event.event_type.value,
            user_id=event.user_id,
            projection_id=event.projection_id,
            product_identity_realm=(
                event.product_identity_realm.value
                if event.product_identity_realm is not None
                else None
            ),
            realm_subject_id=event.realm_subject_id,
            reason_code=event.reason_code,
            correlation_id=event.correlation_id,
            context_jti=event.context_jti,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return IdentityProjectionEvent.model_validate(model)
