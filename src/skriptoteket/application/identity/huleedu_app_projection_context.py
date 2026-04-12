"""Validate signed HuleEdu context for Skriptoteket app projections.

Purpose:
    Keep product-context and provisioning-claim parsing separate from the
    projection resolver's persistence flow.

Relationships:
    - Used by `HuleEduAppProjectionResolver` before lookup or provisioning.
    - Depends only on signed `InternalIdentityContextV1` fields and domain
      validation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.identity.email_validation import validate_email
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.domain.identity.projections import ProductIdentityRealm

ACTIVE_APP_SKRIPTOTEKET = "skriptoteket"
ACCEPTED_PRODUCT_IDENTITY_REALMS = frozenset(
    {
        ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
        ProductIdentityRealm.HULEEDU_SCHOOL,
    }
)


@dataclass(frozen=True, slots=True)
class ProjectionKey:
    """Resolved product realm subject key for local projection lookup."""

    realm: ProductIdentityRealm
    subject_id: str


@dataclass(frozen=True, slots=True)
class ProvisioningClaims:
    """Signed HuleEdu claims trusted enough for local first-login provisioning."""

    email: str
    first_name: str | None
    last_name: str | None
    display_name: str | None
    locale: str


def validate_skriptoteket_product_context(*, context: InternalIdentityContextV1) -> ProjectionKey:
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

    return ProjectionKey(realm=realm, subject_id=context.realm_subject_id)


def provisioning_claims_from_context(
    *,
    context: InternalIdentityContextV1,
) -> ProvisioningClaims | DomainError:
    """Return signed provisioning claims or a fail-closed domain error."""
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

    return ProvisioningClaims(
        email=email,
        first_name=context.given_name,
        last_name=context.family_name,
        display_name=context.display_name,
        locale=context.locale or "sv-SE",
    )


def best_effort_projection_key(*, context: InternalIdentityContextV1) -> ProjectionKey | None:
    """Resolve a projection key for audit events when product context failed validation."""
    if context.active_product_identity_realm is None or context.realm_subject_id is None:
        return None
    try:
        realm = ProductIdentityRealm(context.active_product_identity_realm)
    except ValueError:
        return None
    return ProjectionKey(realm=realm, subject_id=context.realm_subject_id)
