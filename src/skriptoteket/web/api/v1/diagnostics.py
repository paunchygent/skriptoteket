"""Diagnostic API routes for cross-app auth proof.

Purpose:
    Expose narrow, hidden verification surfaces used by provider-owned live
    proof runners without turning diagnostics into product features.

Relationships:
    - The HuleEdu internal identity probe consumes the same signed Gateway
      context verifier as protected Skriptoteket APIs.
    - It validates the app/product context without resolving or creating local
      projections, so provider proof cannot mutate Skriptoteket users.
"""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.huleedu_app_projection_context import (
    validate_skriptoteket_product_context,
)
from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import HuleEduInternalIdentityVerifierProtocol
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


class HuleEduInternalIdentityProbeClaims(BaseModel):
    """Sanitized decoded signed-context claims for provider proof."""

    model_config = ConfigDict(frozen=True)

    context_version: int
    issuer: str
    audience: str
    active_app: str
    active_product_identity_realm: str
    realm_subject_id_present: bool
    subject_claim_present: bool
    subject_matches_realm_subject: bool | None
    linked_identity_realm_present: bool
    linked_identity_matches_realm_subject: bool | None
    email_present: bool
    email_verified: bool | None
    org_id_present: bool
    tenant_id_present: bool
    source_app: str | None
    roles: list[str]
    grants: list[str]
    feature_flags: list[str]
    active_context_keys: list[str]
    policy_version: str
    issued_at: int
    expires_at: int


class HuleEduInternalIdentityProbeResponse(BaseModel):
    """No-secret diagnostic response for HuleEdu live apply artifacts."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    app: Literal["skriptoteket"]
    product_identity_realm: str
    claims: HuleEduInternalIdentityProbeClaims


def _linked_identity_matches_realm_subject(context: InternalIdentityContextV1) -> bool | None:
    if not context.linked_identity_ids or context.active_product_identity_realm is None:
        return None
    linked_subject = context.linked_identity_ids.get(context.active_product_identity_realm)
    if linked_subject is None or context.realm_subject_id is None:
        return None
    return linked_subject == context.realm_subject_id


def _build_sanitized_probe_claims(
    context: InternalIdentityContextV1,
) -> HuleEduInternalIdentityProbeClaims:
    subject_matches_realm_subject: bool | None = None
    if context.realm_subject_id is not None:
        subject_matches_realm_subject = context.sub == context.realm_subject_id

    return HuleEduInternalIdentityProbeClaims(
        context_version=context.context_version,
        issuer=context.iss,
        audience=context.aud,
        active_app=context.active_app or "",
        active_product_identity_realm=context.active_product_identity_realm or "",
        realm_subject_id_present=context.realm_subject_id is not None,
        subject_claim_present=bool(context.sub),
        subject_matches_realm_subject=subject_matches_realm_subject,
        linked_identity_realm_present=(
            context.active_product_identity_realm is not None
            and context.linked_identity_ids is not None
            and context.active_product_identity_realm in context.linked_identity_ids
        ),
        linked_identity_matches_realm_subject=_linked_identity_matches_realm_subject(context),
        email_present=context.email is not None,
        email_verified=context.email_verified,
        org_id_present=context.org_id is not None,
        tenant_id_present=context.tenant_id is not None,
        source_app=context.source_app,
        roles=sorted(context.roles),
        grants=sorted(context.grants),
        feature_flags=sorted(context.feature_flags),
        active_context_keys=sorted((context.active_context or {}).keys()),
        policy_version=context.policy_version,
        issued_at=context.iat,
        expires_at=context.exp,
    )


@router.get(
    "/huleedu-internal-identity",
    response_model=HuleEduInternalIdentityProbeResponse,
)
async def probe_huleedu_internal_identity(
    request: Request,
    verifier: FromDishka[HuleEduInternalIdentityVerifierProtocol],
    clock: FromDishka[ClockProtocol],
) -> HuleEduInternalIdentityProbeResponse:
    """Return sanitized signed-context proof without local projection side effects."""
    context = verifier.verify(
        headers=request.headers,
        now_ts=int(clock.now().timestamp()),
    )
    projection_key = validate_skriptoteket_product_context(context=context)

    return HuleEduInternalIdentityProbeResponse(
        status="ok",
        app="skriptoteket",
        product_identity_realm=projection_key.realm.value,
        claims=_build_sanitized_probe_claims(context),
    )
