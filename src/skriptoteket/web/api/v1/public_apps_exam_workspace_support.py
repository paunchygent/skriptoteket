"""Shared gate and database admission for public Exam Converter workspace routes.

Purpose:
  Keep every public exam workspace request behind the same active-capability gate
  and the same database-backed hourly admission before any parsing or rendering.

Relationships:
  - Reuses the public Exam Converter capability gate for the job and workspace routes.
  - Admits through ``AdmitPublicRequestHandlerProtocol`` with the client IP only.
"""

import structlog
from fastapi import Request

from skriptoteket.domain.curated_apps.models import CuratedAppPublicRuntimeStatus
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestBucket,
)
from skriptoteket.web.api.v1.public_apps import EXAM_CONVERTER_APP_ID, EXAM_CONVERTER_SCOPE
from skriptoteket.web.api.v1.public_apps_support import require_public_curated_app_capability
from skriptoteket.web.request_metadata import forwarded_chain_untrusted, get_client_ip

logger = structlog.get_logger(__name__)

_PROXY_UNTRUSTED_WARNING_EMITTED = False


def _warn_once_when_proxy_chain_untrusted(*, request: Request) -> None:
    """Log once per process when the guest limiter only sees the proxy address.

    No IP addresses or header values are logged: the record carries only the
    stable event name and the operator hint.
    """

    global _PROXY_UNTRUSTED_WARNING_EMITTED
    if _PROXY_UNTRUSTED_WARNING_EMITTED:
        return
    if not forwarded_chain_untrusted(request):
        return
    _PROXY_UNTRUSTED_WARNING_EMITTED = True
    logger.warning(
        "public_guest_limiter_proxy_untrusted",
        reason_code="public_guest_limiter_proxy_untrusted",
        detail=(
            "Guest limiter sees only the proxy address; set TRUSTED_PROXY_CIDRS "
            "to the exact nginx-proxy address so guests keep separate limiter keys."
        ),
    )


def require_active_exam_converter(*, registry: CuratedAppRegistryProtocol) -> None:
    """Fail closed unless the public Exam Converter runtime capability is active."""

    _app, capability = require_public_curated_app_capability(
        app_id=EXAM_CONVERTER_APP_ID,
        scope=EXAM_CONVERTER_SCOPE,
        registry=registry,
    )
    if capability.runtime_status is not CuratedAppPublicRuntimeStatus.ACTIVE:
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Public Exam Converter runtime is not active.",
            details={
                "app_id": EXAM_CONVERTER_APP_ID,
                "capability": EXAM_CONVERTER_SCOPE,
                "reason_code": "public_exam_converter_runtime_inactive",
            },
        )


async def admit_guest_request(
    *,
    request: Request,
    registry: CuratedAppRegistryProtocol,
    admit_handler: AdmitPublicRequestHandlerProtocol,
    bucket: PublicRequestBucket,
) -> None:
    """Admit one guest request through the shared hourly limiter or raise 429."""

    require_active_exam_converter(registry=registry)
    _warn_once_when_proxy_chain_untrusted(request=request)
    client_ip = get_client_ip(request) or "unknown"
    admission = await admit_handler.admit(bucket=bucket, client_ip=client_ip)
    if admission.admitted:
        return
    refusal = admission.refusal
    if refusal is None:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Public request refusal is missing its reason.",
        )
    raise DomainError(
        code=ErrorCode.TOO_MANY_REQUESTS,
        message="Gränsen för gäster är nådd. Logga in för att fortsätta.",
        details={"reason": refusal.value, "bucket": bucket.value},
    )
