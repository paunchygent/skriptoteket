"""Resolve Skriptoteket-local app projections from HuleEdu identity context.

Purpose:
    Convert a verified HuleEdu `InternalIdentityContextV1` subject into the
    local `User` and `UserProfile` that Skriptoteket APIs use for ownership,
    role checks, profile state, and AI preferences.

Relationships:
    - Used by the app-local continuation dependency after HuleEdu header
      verification succeeds.
    - Depends on identity repository protocols and keeps local authorization
      owned by Skriptoteket.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.domain.identity.models import AuthProvider, User, UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

ACTIVE_APP_SKRIPTOTEKET = "skriptoteket"
ACCEPTED_PRODUCT_IDENTITY_REALMS = frozenset({"skriptoteket_standalone", "huleedu_school"})


class HuleEduAppUserProjection(BaseModel):
    """Skriptoteket-local user/profile resolved from a verified HuleEdu subject."""

    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile


def validate_skriptoteket_product_context(*, context: InternalIdentityContextV1) -> None:
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

    if context.realm_subject_id is None:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid HuleEdu product context for Skriptoteket",
            details={"reason": "invalid_huleedu_product_context", "field": "realm_subject_id"},
        )


class HuleEduAppProjectionResolver(HuleEduAppProjectionResolverProtocol):
    """Resolve existing HuleEdu-linked local users without browser-session fallback."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._clock = clock

    async def resolve(self, *, context: InternalIdentityContextV1) -> HuleEduAppUserProjection:
        """Resolve the local projection for one verified HuleEdu subject.

        Raises:
            DomainError: If no active local projection exists for the HuleEdu subject.
        """
        validate_skriptoteket_product_context(context=context)

        async with self._uow:
            user = await self._users.get_by_auth_provider_external_id(
                auth_provider=AuthProvider.HULEEDU,
                external_id=context.sub,
            )
            if user is None or not user.is_active:
                raise DomainError(
                    code=ErrorCode.UNAUTHORIZED,
                    message="Missing Skriptoteket app projection for HuleEdu identity",
                    details={"reason": "missing_huleedu_app_projection"},
                )

            profile = await self._profiles.get_by_user_id(user_id=user.id)
            if profile is None:
                now = self._clock.now()
                profile = await self._profiles.create(
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

        return HuleEduAppUserProjection(user=user, profile=profile)
