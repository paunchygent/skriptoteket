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

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.email_validation import validate_email
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    IdentityProjectionEventType,
    ProductIdentityRealm,
)
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

ACTIVE_APP_SKRIPTOTEKET = "skriptoteket"
ACCEPTED_PRODUCT_IDENTITY_REALMS = frozenset(
    {
        ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
        ProductIdentityRealm.HULEEDU_SCHOOL,
    }
)


class HuleEduAppUserProjection(BaseModel):
    """Skriptoteket-local user/profile resolved from a verified HuleEdu subject."""

    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile


@dataclass(frozen=True, slots=True)
class _ProjectionKey:
    realm: ProductIdentityRealm
    subject_id: str


@dataclass(frozen=True, slots=True)
class _ProvisioningClaims:
    email: str
    first_name: str | None
    last_name: str | None
    display_name: str | None
    locale: str


def validate_skriptoteket_product_context(*, context: InternalIdentityContextV1) -> _ProjectionKey:
    """Fail closed when HuleEdu context is not scoped to Skriptoteket."""
    if context.active_app != ACTIVE_APP_SKRIPTOTEKET:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={"reason": "invalid_huleedu_product_context", "field": "active_app"},
        )

    if context.active_product_identity_realm not in ACCEPTED_PRODUCT_IDENTITY_REALMS:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={
                "reason": "invalid_huleedu_product_context",
                "field": "active_product_identity_realm",
            },
        )

    try:
        realm = ProductIdentityRealm(context.active_product_identity_realm)
    except ValueError as exc:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={
                "reason": "invalid_huleedu_product_context",
                "field": "active_product_identity_realm",
            },
        ) from exc

    if realm not in ACCEPTED_PRODUCT_IDENTITY_REALMS:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={
                "reason": "invalid_huleedu_product_context",
                "field": "active_product_identity_realm",
            },
        )

    if context.realm_subject_id is None:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={"reason": "invalid_huleedu_product_context", "field": "realm_subject_id"},
        )

    return _ProjectionKey(realm=realm, subject_id=context.realm_subject_id)


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
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._projections = projections
        self._projection_events = projection_events
        self._clock = clock
        self._id_generator = id_generator

    async def resolve(self, *, context: InternalIdentityContextV1) -> HuleEduAppUserProjection:
        """Resolve the local projection for one verified HuleEdu subject.

        Raises:
            DomainError: If no active local projection exists for the HuleEdu subject.
        """
        try:
            projection_key = validate_skriptoteket_product_context(context=context)
        except DomainError as exc:
            await self._record_invalid_context(context=context, error=exc)
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
                user = await self._users.get_by_id(projection.user_id)
                if user is None or not user.is_active:
                    failure = await self._record_failure(
                        event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                        projection_key=projection_key,
                        projection=projection,
                        context=context,
                        reason_code="inactive_or_missing_local_user",
                        message="Missing active Skriptoteket user for HuleEdu identity projection",
                    )
                else:
                    profile = await self._ensure_profile(user=user)
                    await self._record_event(
                        event_type=IdentityProjectionEventType.RESOLVED,
                        projection_key=projection_key,
                        projection=projection,
                        user=user,
                        context=context,
                        reason_code="projection_resolved",
                    )
                    resolved = HuleEduAppUserProjection(user=user, profile=profile)
            else:
                claims_or_error = self._provisioning_claims(context=context)
                if isinstance(claims_or_error, DomainError):
                    failure = await self._record_failure(
                        event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                        projection_key=projection_key,
                        projection=None,
                        context=context,
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
                            reason_code="identity_linking_required",
                            message=(
                                "Skriptoteket identity linking is required for this HuleEdu email"
                            ),
                            field="email",
                        )
                    else:
                        resolved = await self._provision_user_projection(
                            projection_key=projection_key,
                            claims=claims_or_error,
                            context=context,
                        )

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

    def _provisioning_claims(
        self,
        *,
        context: InternalIdentityContextV1,
    ) -> _ProvisioningClaims | DomainError:
        if context.email is None:
            return DomainError(
                code=ErrorCode.UNAUTHORIZED,
                message="Missing signed email claim for HuleEdu provisioning",
                details={"reason": "missing_huleedu_app_projection", "field": "email"},
            )
        try:
            email = validate_email(email=context.email)
        except DomainError:
            return DomainError(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid signed email claim for HuleEdu provisioning",
                details={"reason": "missing_huleedu_app_projection", "field": "email"},
            )

        if context.email_verified is not True:
            return DomainError(
                code=ErrorCode.UNAUTHORIZED,
                message="Missing verified signed email claim for HuleEdu provisioning",
                details={
                    "reason": "missing_huleedu_app_projection",
                    "field": "email_verified",
                },
            )

        return _ProvisioningClaims(
            email=email,
            first_name=context.given_name,
            last_name=context.family_name,
            display_name=context.display_name,
            locale=context.locale or "sv-SE",
        )

    async def _provision_user_projection(
        self,
        *,
        projection_key: _ProjectionKey,
        claims: _ProvisioningClaims,
        context: InternalIdentityContextV1,
    ) -> HuleEduAppUserProjection:
        now = self._clock.now()
        user = await self._users.create(
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
        projection = await self._projections.create(
            projection=IdentityProjection(
                id=self._id_generator.new_uuid(),
                user_id=user.id,
                product_identity_realm=projection_key.realm,
                realm_subject_id=projection_key.subject_id,
                created_at=now,
                updated_at=now,
            )
        )
        await self._record_event(
            event_type=IdentityProjectionEventType.PROVISIONED,
            projection_key=projection_key,
            projection=projection,
            user=user,
            context=context,
            reason_code="projection_provisioned",
        )
        return HuleEduAppUserProjection(user=user, profile=profile)

    async def _record_invalid_context(
        self,
        *,
        context: InternalIdentityContextV1,
        error: DomainError,
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
                projection_key=self._best_effort_projection_key(context=context),
                projection=None,
                user=None,
                context=context,
                reason_code=f"invalid_{field}",
            )

    async def _record_failure(
        self,
        *,
        event_type: IdentityProjectionEventType,
        projection_key: _ProjectionKey,
        projection: IdentityProjection | None,
        context: InternalIdentityContextV1,
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
        projection_key: _ProjectionKey | None,
        projection: IdentityProjection | None,
        user: User | None,
        context: InternalIdentityContextV1,
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
                correlation_id=None,
                context_jti=context.jti,
                created_at=now,
            )
        )

    def _best_effort_projection_key(
        self,
        *,
        context: InternalIdentityContextV1,
    ) -> _ProjectionKey | None:
        if context.active_product_identity_realm is None or context.realm_subject_id is None:
            return None
        try:
            realm = ProductIdentityRealm(context.active_product_identity_realm)
        except ValueError:
            return None
        return _ProjectionKey(realm=realm, subject_id=context.realm_subject_id)
