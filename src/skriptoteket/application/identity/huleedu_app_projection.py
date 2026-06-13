"""Resolve Skriptoteket-local app projections from HuleEdu identity context.

Purpose:
    Convert a verified HuleEdu `InternalIdentityContextV1` realm subject into
    the local `User` and `UserProfile` that Skriptoteket APIs use for ownership,
    role checks, profile state, and AI preferences.

Relationships:
    - Used by the app-local continuation dependency after HuleEdu header
      verification succeeds.
    - Depends on identity projection repository protocols and keeps local
      authorization owned by Skriptoteket.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.huleedu_app_projection_context import (
    ProjectionKey,
    ProvisioningClaims,
    best_effort_projection_key,
    provisioning_claims_from_context,
    validate_skriptoteket_product_context,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    IdentityProjectionEventType,
)
from skriptoteket.protocols.auth_outcomes import AuthOutcomeRecorderProtocol, AuthProjectionOutcome
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class HuleEduAppUserProjection(BaseModel):
    """Skriptoteket-local user/profile resolved from a verified HuleEdu subject."""

    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile
    realm_subject_id: str


@dataclass(frozen=True, slots=True)
class _ProvisioningEmailConflict:
    pass


@dataclass(frozen=True, slots=True)
class _ProvisioningProjectionConflict:
    pass


class _ProjectionAlreadyExists(Exception):
    """Internal signal used to roll back nested provisioning writes."""


class HuleEduAppProjectionResolver(HuleEduAppProjectionResolverProtocol):
    """Resolve or provision HuleEdu-derived local users without browser-session fallback."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        projections: IdentityProjectionRepositoryProtocol,
        projection_events: IdentityProjectionEventRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        auth_outcomes: AuthOutcomeRecorderProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._projections = projections
        self._projection_events = projection_events
        self._clock = clock
        self._id_generator = id_generator
        self._auth_outcomes = auth_outcomes

    async def resolve(
        self,
        *,
        context: InternalIdentityContextV1,
        correlation_id: UUID | None = None,
    ) -> HuleEduAppUserProjection:
        """Resolve the local projection for one verified HuleEdu subject.

        Raises:
            DomainError: If no active local projection exists for the HuleEdu subject.
        """
        try:
            projection_key = validate_skriptoteket_product_context(context=context)
        except DomainError as exc:
            await self._record_invalid_context(
                context=context,
                error=exc,
                correlation_id=correlation_id,
            )
            raise

        resolved: HuleEduAppUserProjection | None = None
        failure: DomainError | None = None

        async with self._uow:
            await self._projections.lock_realm_subject(
                product_identity_realm=projection_key.realm.value,
                realm_subject_id=projection_key.subject_id,
            )
            projection = await self._projections.get_by_realm_subject(
                product_identity_realm=projection_key.realm.value,
                realm_subject_id=projection_key.subject_id,
            )
            if projection is not None:
                projection_result = await self._resolve_existing_projection(
                    projection_key=projection_key,
                    projection=projection,
                    context=context,
                    reason_code="projection_resolved",
                    correlation_id=correlation_id,
                )
                if isinstance(projection_result, DomainError):
                    failure = projection_result
                else:
                    resolved = projection_result
            else:
                claims_or_error = provisioning_claims_from_context(context=context)
                if isinstance(claims_or_error, DomainError):
                    failure = await self._record_failure(
                        event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                        projection_key=projection_key,
                        projection=None,
                        context=context,
                        correlation_id=correlation_id,
                        reason_code=str(
                            claims_or_error.details.get(
                                "reason",
                                "missing_huleedu_app_projection",
                            )
                        ),
                        message=claims_or_error.message,
                        field=claims_or_error.details.get("field"),
                    )
                else:
                    await self._projections.lock_email(email=claims_or_error.email)
                    existing_user_auth = await self._users.get_auth_by_email(claims_or_error.email)
                    if existing_user_auth is not None:
                        failure = await self._record_failure(
                            event_type=IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED,
                            projection_key=projection_key,
                            projection=None,
                            context=context,
                            correlation_id=correlation_id,
                            reason_code="identity_linking_required",
                            message=(
                                "Skriptoteket identity linking is required for this HuleEdu email"
                            ),
                            field="email",
                        )
                    else:
                        provisioning_result = await self._provision_user_projection(
                            projection_key=projection_key,
                            claims=claims_or_error,
                            context=context,
                            correlation_id=correlation_id,
                        )
                        if isinstance(provisioning_result, _ProvisioningEmailConflict):
                            failure = await self._record_failure(
                                event_type=(
                                    IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED
                                ),
                                projection_key=projection_key,
                                projection=None,
                                context=context,
                                correlation_id=correlation_id,
                                reason_code="identity_linking_required",
                                message=(
                                    "Skriptoteket identity linking is required for this HuleEdu "
                                    "email"
                                ),
                                field="email",
                            )
                        elif isinstance(provisioning_result, _ProvisioningProjectionConflict):
                            projection = await self._projections.get_by_realm_subject(
                                product_identity_realm=projection_key.realm.value,
                                realm_subject_id=projection_key.subject_id,
                            )
                            if projection is None:
                                failure = await self._record_failure(
                                    event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                                    projection_key=projection_key,
                                    projection=None,
                                    context=context,
                                    correlation_id=correlation_id,
                                    reason_code="projection_conflict_unresolved",
                                    message=(
                                        "Missing Skriptoteket app projection after conflict "
                                        "recovery"
                                    ),
                                )
                            else:
                                projection_result = await self._resolve_existing_projection(
                                    projection_key=projection_key,
                                    projection=projection,
                                    context=context,
                                    reason_code="projection_conflict_recovered",
                                    correlation_id=correlation_id,
                                )
                                if isinstance(projection_result, DomainError):
                                    failure = projection_result
                                else:
                                    resolved = projection_result
                        else:
                            resolved = provisioning_result

        if failure is not None:
            raise failure
        if resolved is None:
            raise DomainError(
                code=ErrorCode.UNAUTHORIZED,
                message="Missing Skriptoteket app projection for HuleEdu identity",
                details={"reason": "missing_huleedu_app_projection"},
            )
        return resolved

    async def _ensure_profile(self, *, user: User) -> UserProfile:
        profile = await self._profiles.get_by_user_id(user_id=user.id)
        if profile is not None:
            return profile

        now = self._clock.now()
        return await self._profiles.create(
            profile=UserProfile(
                user_id=user.id,
                first_name=None,
                last_name=None,
                display_name=None,
                allow_remote_fallback=None,
                inline_completion_provider=None,
                locale="sv-SE",
                created_at=now,
                updated_at=now,
            )
        )

    async def _resolve_existing_projection(
        self,
        *,
        projection_key: ProjectionKey,
        projection: IdentityProjection,
        context: InternalIdentityContextV1,
        reason_code: str,
        correlation_id: UUID | None,
    ) -> HuleEduAppUserProjection | DomainError:
        user = await self._users.get_by_id(projection.user_id)
        if user is None or not user.is_active:
            return await self._record_failure(
                event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                projection_key=projection_key,
                projection=projection,
                context=context,
                correlation_id=correlation_id,
                reason_code="inactive_or_missing_local_user",
                message="Missing active Skriptoteket user for HuleEdu identity projection",
            )

        profile = await self._ensure_profile(user=user)
        await self._record_event(
            event_type=IdentityProjectionEventType.RESOLVED,
            projection_key=projection_key,
            projection=projection,
            user=user,
            context=context,
            correlation_id=correlation_id,
            reason_code=reason_code,
        )
        return HuleEduAppUserProjection(
            user=user,
            profile=profile,
            realm_subject_id=projection_key.subject_id,
        )

    async def _provision_user_projection(
        self,
        *,
        projection_key: ProjectionKey,
        claims: ProvisioningClaims,
        context: InternalIdentityContextV1,
        correlation_id: UUID | None,
    ) -> HuleEduAppUserProjection | _ProvisioningEmailConflict | _ProvisioningProjectionConflict:
        now = self._clock.now()
        try:
            async with self._uow:
                user = await self._users.create_if_email_available(
                    user=User(
                        id=self._id_generator.new_uuid(),
                        email=claims.email,
                        role=Role.USER,
                        auth_provider=AuthProvider.HULEEDU,
                        is_active=True,
                        email_verified=True,
                        failed_login_attempts=0,
                        locked_until=None,
                        last_login_at=None,
                        last_failed_login_at=None,
                        created_at=now,
                        updated_at=now,
                    ),
                    password_hash=None,
                )
                if user is None:
                    return _ProvisioningEmailConflict()

                profile = await self._profiles.create(
                    profile=UserProfile(
                        user_id=user.id,
                        first_name=claims.first_name,
                        last_name=claims.last_name,
                        display_name=claims.display_name,
                        allow_remote_fallback=None,
                        inline_completion_provider=None,
                        locale=claims.locale,
                        created_at=now,
                        updated_at=now,
                    )
                )
                projection = await self._projections.create_if_realm_subject_absent(
                    projection=IdentityProjection(
                        id=self._id_generator.new_uuid(),
                        user_id=user.id,
                        product_identity_realm=projection_key.realm,
                        realm_subject_id=projection_key.subject_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
                if projection is None:
                    raise _ProjectionAlreadyExists

                await self._record_event(
                    event_type=IdentityProjectionEventType.PROVISIONED,
                    projection_key=projection_key,
                    projection=projection,
                    user=user,
                    context=context,
                    correlation_id=correlation_id,
                    reason_code="projection_provisioned",
                )
                return HuleEduAppUserProjection(
                    user=user,
                    profile=profile,
                    realm_subject_id=projection_key.subject_id,
                )
        except _ProjectionAlreadyExists:
            return _ProvisioningProjectionConflict()

    async def _record_invalid_context(
        self,
        *,
        context: InternalIdentityContextV1,
        error: DomainError,
        correlation_id: UUID | None,
    ) -> None:
        field = str(error.details.get("field", "unknown"))
        event_type = (
            IdentityProjectionEventType.UNSUPPORTED_REALM
            if field == "active_product_identity_realm"
            else IdentityProjectionEventType.BLOCKED_PROVISIONING
        )
        async with self._uow:
            await self._record_event(
                event_type=event_type,
                projection_key=best_effort_projection_key(context=context),
                projection=None,
                user=None,
                context=context,
                correlation_id=correlation_id,
                reason_code=f"invalid_{field}",
            )

    async def _record_failure(
        self,
        *,
        event_type: IdentityProjectionEventType,
        projection_key: ProjectionKey,
        projection: IdentityProjection | None,
        context: InternalIdentityContextV1,
        correlation_id: UUID | None,
        reason_code: str,
        message: str,
        field: object | None = None,
    ) -> DomainError:
        await self._record_event(
            event_type=event_type,
            projection_key=projection_key,
            projection=projection,
            user=None,
            context=context,
            correlation_id=correlation_id,
            reason_code=reason_code,
        )
        details: dict[str, object] = {"reason": reason_code}
        if field is not None:
            details["field"] = field
        return DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            details=details,
        )

    async def _record_event(
        self,
        *,
        event_type: IdentityProjectionEventType,
        projection_key: ProjectionKey | None,
        projection: IdentityProjection | None,
        user: User | None,
        context: InternalIdentityContextV1,
        correlation_id: UUID | None,
        reason_code: str,
    ) -> None:
        now = self._clock.now()
        await self._projection_events.create(
            event=IdentityProjectionEvent(
                id=self._id_generator.new_uuid(),
                event_type=event_type,
                user_id=user.id if user is not None else projection.user_id if projection else None,
                projection_id=projection.id if projection else None,
                product_identity_realm=projection_key.realm if projection_key else None,
                realm_subject_id=projection_key.subject_id if projection_key else None,
                reason_code=reason_code,
                correlation_id=correlation_id,
                context_jti=context.jti,
                created_at=now,
            )
        )
        self._auth_outcomes.record_projection_outcome(
            realm=projection_key.realm.value if projection_key else None,
            outcome=_projection_outcome(event_type=event_type, reason_code=reason_code),
            reason=reason_code,
            correlation_id=correlation_id,
        )


def _projection_outcome(
    *,
    event_type: IdentityProjectionEventType,
    reason_code: str,
) -> AuthProjectionOutcome:
    if event_type is IdentityProjectionEventType.RESOLVED:
        return "resolved"
    if event_type is IdentityProjectionEventType.PROVISIONED:
        return "provisioned"
    if event_type is IdentityProjectionEventType.UNSUPPORTED_REALM:
        return "unsupported_realm"
    if event_type is IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED:
        return "linking_required"
    if reason_code == "missing_huleedu_app_projection":
        return "missing"
    return "blocked_provisioning"
