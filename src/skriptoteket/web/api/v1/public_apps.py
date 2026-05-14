"""Public curated-app bootstrap routes for dedicated guest entry hosts.

Purpose:
    Expose a public-safe curated-app bootstrap contract under
    `/api/v1/public/apps/{app_id}` without weakening the existing authenticated
    `/api/v1/apps/{app_id}` seam.

Relationships:
    - Reads the canonical `public_access_profile` from the curated-app registry.
    - Returns only public-safe metadata needed by the dedicated public SPA host.
    - Intentionally ignores ambient session cookies and owner-scoped authority.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.public_apps_support import (
    require_public_curated_app,
    require_public_curated_app_capability,
)
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1/public/apps", tags=["public-apps"])

EXAM_CONVERTER_APP_ID = "documents.conversion_hub"
EXAM_CONVERTER_SCOPE = "exam_converter"
EXAM_CONVERTER_ROUTE_SLUG = "exam-converter"
EXAM_CONVERTER_PUBLIC_FRONTEND_ROUTE = (
    f"/public/apps/{EXAM_CONVERTER_APP_ID}/{EXAM_CONVERTER_ROUTE_SLUG}"
)
EXAM_CONVERTER_PUBLIC_API_NAMESPACE = (
    f"/api/v1/public/apps/{EXAM_CONVERTER_APP_ID}/{EXAM_CONVERTER_ROUTE_SLUG}"
)

_CAPABILITY_SCOPE_BY_ROUTE_SLUG = {EXAM_CONVERTER_ROUTE_SLUG: EXAM_CONVERTER_SCOPE}
_EXAM_CONVERTER_ALLOWED_CONTENT_TYPES = [
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
]
_EXAM_CONVERTER_ALLOWED_FILE_SUFFIXES = [".dxe", ".pdf"]
_EXAM_CONVERTER_ARTIFACT_KEYS = [
    "examnet_pdf",
    "manual_follow_up_report",
    "qti_package",
    "qti_validation_report",
    "warnings_report",
]
_EXAM_CONVERTER_BLOCKED_AFFORDANCES = [
    "authenticated_route_discovery",
    "arbitrary_conversion_routes",
    "vault_or_myfiles_save",
    "owner_job_recovery",
    "account_history",
]
_EXAM_CONVERTER_REASON_CODES = [
    "public_exam_converter_empty_payload",
    "public_exam_converter_artifact_not_ready",
    "public_exam_converter_concurrency_limited",
    "public_exam_converter_grant_authority_failed",
    "public_exam_converter_grant_authority_unconfigured",
    "public_exam_converter_invalid_grant_payload",
    "public_exam_converter_invalid_target",
    "public_exam_converter_missing_filename",
    "public_exam_converter_missing_dxe",
    "public_exam_converter_payload_too_large",
    "public_exam_converter_rate_limited",
    "public_exam_converter_runtime_inactive",
    "public_exam_converter_time_budget_exceeded",
    "public_exam_converter_unsupported_content_type",
    "public_exam_converter_unsupported_file_type",
    "public_exam_converter_upstream_unavailable",
]
_EXAM_CONVERTER_TARGETS = ["examnet_pdf", "qti_package"]
_EXAM_CONVERTER_TELEMETRY = [
    "correlation_id",
    "reason_code",
    "payload_bytes",
    "target_count",
    "no_filename_or_content_capture",
    "no_account_or_owner_identifier",
]
_EXAM_CONVERTER_BLOCKED_AUTHORITY_EXPOSURE = [
    "raw_conversion_grant",
    "raw_artifact_read_lease",
    "huleedu_signing_material",
    "sir_convert_credentials",
    "direct_upstream_host",
]

PublicCapabilityAction = Literal[
    "submit",
    "poll",
    "result",
    "artifact_manifest",
    "artifact_download",
]
PublicCapabilityActionMethod = Literal["GET", "POST"]


class PublicCapabilityRateLimit(BaseModel):
    """Public capability rate-limit metadata."""

    model_config = ConfigDict(frozen=True)

    max_requests: int
    window_seconds: int


class PublicCapabilityUploadLimit(BaseModel):
    """Public capability upload-size cap for one accepted input lane."""

    model_config = ConfigDict(frozen=True)

    field: str
    required: bool
    max_bytes: int


class PublicCapabilityActionAffordance(BaseModel):
    """Browser-visible public action metadata for a scoped capability."""

    model_config = ConfigDict(frozen=True)

    action: PublicCapabilityAction
    method: PublicCapabilityActionMethod
    path_template: str
    enabled: bool


class PublicCapabilityAuthorityBoundary(BaseModel):
    """Public-safe authority semantics for a scoped capability."""

    model_config = ConfigDict(frozen=True)

    browser_authority: Literal["opaque_public_handles_only"]
    upstream_calls: Literal["server_mediated_public_conversion"]
    artifact_reads: Literal["server_mediated_artifact_download"]
    account_authority: Literal["ignored"]
    persistence: Literal["transient_public_only"]
    blocked_exposure: list[str]


class PublicCapabilityMetadata(BaseModel):
    """Public-safe scoped capability metadata."""

    model_config = ConfigDict(frozen=True)

    scope: str
    profile: CuratedAppPublicAccessProfile
    frontend_route: str
    api_namespace: str
    runtime_status: CuratedAppPublicRuntimeStatus
    action_affordances: list[PublicCapabilityActionAffordance]
    authority_boundary: PublicCapabilityAuthorityBoundary
    allowed_content_types: list[str]
    allowed_file_suffixes: list[str]
    upload_limits: list[PublicCapabilityUploadLimit]
    request_time_budget_seconds: int
    concurrency_limit: int
    rate_limit: PublicCapabilityRateLimit
    artifact_ttl_seconds: int
    target_vocabulary: list[str]
    artifact_manifest_schema: Literal["digiexam_migration_bundle_v1"]
    artifact_keys: list[str]
    reason_codes: list[str]
    blocked_affordances: list[str]
    telemetry: list[str]


class PublicAppBootstrapResponse(BaseModel):
    """Public-safe bootstrap payload for a curated app public host."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str | None
    ui_mode: CuratedAppUiMode
    public_access_profile: CuratedAppPublicAccessProfile
    host_mode: Literal["public"] = "public"


class PublicAppCapabilityBootstrapResponse(BaseModel):
    """Public-safe bootstrap payload for a scoped curated-app capability."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str | None
    ui_mode: CuratedAppUiMode
    public_access_profile: CuratedAppPublicAccessProfile
    public_capability: PublicCapabilityMetadata
    host_mode: Literal["public"] = "public"


def _capability_scope_from_route_slug(*, route_slug: str) -> str:
    return _CAPABILITY_SCOPE_BY_ROUTE_SLUG.get(route_slug.strip(), "")


def _build_exam_converter_action_affordances(
    *, runtime_status: CuratedAppPublicRuntimeStatus
) -> list[PublicCapabilityActionAffordance]:
    if runtime_status is CuratedAppPublicRuntimeStatus.CONTRACT_ONLY:
        return []

    runtime_enabled = runtime_status is CuratedAppPublicRuntimeStatus.ACTIVE
    return [
        PublicCapabilityActionAffordance(
            action="submit",
            method="POST",
            path_template=f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs",
            enabled=runtime_enabled,
        ),
        PublicCapabilityActionAffordance(
            action="poll",
            method="GET",
            path_template=f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs/{{public_job_id}}",
            enabled=runtime_enabled,
        ),
        PublicCapabilityActionAffordance(
            action="result",
            method="GET",
            path_template=f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs/{{public_job_id}}/result",
            enabled=runtime_enabled,
        ),
        PublicCapabilityActionAffordance(
            action="artifact_manifest",
            method="GET",
            path_template=(
                f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs/{{public_job_id}}/artifacts"
            ),
            enabled=runtime_enabled,
        ),
        PublicCapabilityActionAffordance(
            action="artifact_download",
            method="GET",
            path_template=(
                f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs/"
                "{public_job_id}/artifacts/{artifact_key}/download"
            ),
            enabled=runtime_enabled,
        ),
    ]


def _build_exam_converter_authority_boundary() -> PublicCapabilityAuthorityBoundary:
    return PublicCapabilityAuthorityBoundary(
        browser_authority="opaque_public_handles_only",
        upstream_calls="server_mediated_public_conversion",
        artifact_reads="server_mediated_artifact_download",
        account_authority="ignored",
        persistence="transient_public_only",
        blocked_exposure=_EXAM_CONVERTER_BLOCKED_AUTHORITY_EXPOSURE,
    )


def _build_exam_converter_capability_metadata(
    *, capability: CuratedAppPublicCapability
) -> PublicCapabilityMetadata:
    return PublicCapabilityMetadata(
        scope=capability.scope,
        profile=capability.profile,
        frontend_route=EXAM_CONVERTER_PUBLIC_FRONTEND_ROUTE,
        api_namespace=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
        runtime_status=capability.runtime_status,
        action_affordances=_build_exam_converter_action_affordances(
            runtime_status=capability.runtime_status,
        ),
        authority_boundary=_build_exam_converter_authority_boundary(),
        allowed_content_types=_EXAM_CONVERTER_ALLOWED_CONTENT_TYPES,
        allowed_file_suffixes=_EXAM_CONVERTER_ALLOWED_FILE_SUFFIXES,
        upload_limits=[
            PublicCapabilityUploadLimit(
                field="source_dxe",
                required=True,
                max_bytes=20_000_000,
            ),
            PublicCapabilityUploadLimit(
                field="graded_result_pdf",
                required=False,
                max_bytes=20_000_000,
            ),
        ],
        request_time_budget_seconds=120,
        concurrency_limit=1,
        rate_limit=PublicCapabilityRateLimit(max_requests=3, window_seconds=60),
        artifact_ttl_seconds=3600,
        target_vocabulary=_EXAM_CONVERTER_TARGETS,
        artifact_manifest_schema="digiexam_migration_bundle_v1",
        artifact_keys=_EXAM_CONVERTER_ARTIFACT_KEYS,
        reason_codes=_EXAM_CONVERTER_REASON_CODES,
        blocked_affordances=_EXAM_CONVERTER_BLOCKED_AFFORDANCES,
        telemetry=_EXAM_CONVERTER_TELEMETRY,
    )


def _build_scoped_bootstrap_response(
    *,
    app: CuratedAppDefinition,
    capability: CuratedAppPublicCapability,
) -> PublicAppCapabilityBootstrapResponse:
    if app.app_id != EXAM_CONVERTER_APP_ID or capability.scope != EXAM_CONVERTER_SCOPE:
        raise ValueError("unsupported public capability bootstrap contract")

    return PublicAppCapabilityBootstrapResponse(
        app_id=app.app_id,
        title="Exam Converter",
        summary=(
            "Konvertera DigiExam-prov till Exam.net PDF och QTI-paket utan "
            "inloggning eller kontoanknuten historik."
        ),
        ui_mode=app.ui_mode,
        public_access_profile=app.public_access_profile,
        public_capability=_build_exam_converter_capability_metadata(capability=capability),
    )


@router.get("/{app_id}", response_model=PublicAppBootstrapResponse)
async def get_public_app_bootstrap(
    app_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
) -> PublicAppBootstrapResponse:
    app = require_public_curated_app(app_id=app_id, registry=registry)

    return PublicAppBootstrapResponse(
        app_id=app.app_id,
        title=app.title,
        summary=app.summary,
        ui_mode=app.ui_mode,
        public_access_profile=app.public_access_profile,
    )


@router.get("/{app_id}/{capability_slug}", response_model=PublicAppCapabilityBootstrapResponse)
async def get_public_app_capability_bootstrap(
    app_id: str,
    capability_slug: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
) -> PublicAppCapabilityBootstrapResponse:
    scope = _capability_scope_from_route_slug(route_slug=capability_slug)
    app, capability = require_public_curated_app_capability(
        app_id=app_id,
        scope=scope,
        registry=registry,
    )

    return _build_scoped_bootstrap_response(app=app, capability=capability)
