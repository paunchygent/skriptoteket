"""Route tests for public curated-app bootstrap lookups."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from skriptoteket.application.curated_apps.sir_convert_contracts import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1 import public_apps as public_apps_api


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _make_app(
    *,
    app_id: str = "classroom.group-seating-studio",
    public_access_profile: CuratedAppPublicAccessProfile = (
        CuratedAppPublicAccessProfile.PUBLIC_BROWSER_WORKSPACE_WITH_UPGRADE
    ),
    public_capabilities: list[CuratedAppPublicCapability] | None = None,
) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Klassrumskartan",
        summary="Skapa sittplatsscheman och grupper automatiskt.",
        min_role=Role.USER,
        public_access_profile=public_access_profile,
        public_capabilities=public_capabilities or [],
        placements=[
            CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt"),
        ],
    )


@pytest.mark.asyncio
async def test_get_public_app_bootstrap_returns_public_safe_metadata() -> None:
    app = _make_app()
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    response = await _unwrap_dishka(public_apps_api.get_public_app_bootstrap)(
        app_id=app.app_id,
        registry=registry,
    )

    assert response.app_id == "classroom.group-seating-studio"
    assert response.title == "Klassrumskartan"
    assert response.ui_mode is CuratedAppUiMode.BESPOKE_REQUIRED
    assert (
        response.public_access_profile
        is CuratedAppPublicAccessProfile.PUBLIC_BROWSER_WORKSPACE_WITH_UPGRADE
    )
    assert response.host_mode == "public"


@pytest.mark.asyncio
async def test_get_public_app_bootstrap_fails_closed_for_authenticated_only_apps() -> None:
    app = _make_app(
        app_id="games.flunk_out_frenzy",
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
    )
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(public_apps_api.get_public_app_bootstrap)(
            app_id=app.app_id,
            registry=registry,
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_public_app_bootstrap_fails_closed_for_conversion_hub_general_surface() -> None:
    app = _make_app(
        app_id="documents.conversion_hub",
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                runtime_status=CuratedAppPublicRuntimeStatus.ACTIVE,
            )
        ],
    )
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(public_apps_api.get_public_app_bootstrap)(
            app_id=app.app_id,
            registry=registry,
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_public_app_capability_bootstrap_returns_active_exam_converter_contract() -> None:
    app = _make_app(
        app_id="documents.conversion_hub",
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                runtime_status=CuratedAppPublicRuntimeStatus.ACTIVE,
            )
        ],
    )
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    response = await _unwrap_dishka(public_apps_api.get_public_app_capability_bootstrap)(
        app_id=app.app_id,
        capability_slug="exam-converter",
        registry=registry,
    )

    assert response.app_id == "documents.conversion_hub"
    assert response.title == "Exam Converter"
    assert response.public_access_profile is CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY
    assert response.public_capability.scope == "exam_converter"
    assert (
        response.public_capability.profile is CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME
    )
    assert (
        response.public_capability.frontend_route
        == "/public/apps/documents.conversion_hub/exam-converter"
    )
    assert (
        response.public_capability.api_namespace
        == "/api/v1/public/apps/documents.conversion_hub/exam-converter"
    )
    assert response.public_capability.runtime_status is CuratedAppPublicRuntimeStatus.ACTIVE
    assert [affordance.action for affordance in response.public_capability.action_affordances] == [
        "submit",
        "poll",
        "result",
        "artifact_manifest",
        "artifact_download",
    ]
    assert {affordance.enabled for affordance in response.public_capability.action_affordances} == {
        True
    }
    assert (
        response.public_capability.authority_boundary.browser_authority
        == "opaque_public_handles_only"
    )
    assert (
        response.public_capability.authority_boundary.upstream_calls
        == "server_mediated_public_conversion"
    )
    assert "raw_conversion_grant" in response.public_capability.authority_boundary.blocked_exposure
    assert "direct_upstream_host" in response.public_capability.authority_boundary.blocked_exposure
    assert response.public_capability.target_vocabulary == ["examnet_pdf", "qti_package"]
    assert (
        response.public_capability.artifact_manifest_schema
        == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
    )
    assert "manual_follow_up_report" in response.public_capability.artifact_keys
    assert "target_readiness_report" in response.public_capability.artifact_keys
    assert "public_exam_converter_rate_limited" in response.public_capability.reason_codes
    assert "vault_or_myfiles_save" in response.public_capability.blocked_affordances
    assert "authenticated_route_discovery" in response.public_capability.blocked_affordances
    assert "no_account_or_owner_identifier" in response.public_capability.telemetry


@pytest.mark.asyncio
async def test_get_public_app_capability_bootstrap_fails_closed_for_unsupported_scope() -> None:
    app = _make_app(
        app_id="documents.conversion_hub",
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
            )
        ],
    )
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(public_apps_api.get_public_app_capability_bootstrap)(
            app_id=app.app_id,
            capability_slug="anything-else",
            registry=registry,
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


def test_exam_converter_metadata_states_control_action_affordances() -> None:
    contract_only = public_apps_api._build_exam_converter_capability_metadata(
        capability=CuratedAppPublicCapability(
            scope="exam_converter",
            profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
        )
    )
    grant_ready = public_apps_api._build_exam_converter_capability_metadata(
        capability=CuratedAppPublicCapability(
            scope="exam_converter",
            profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
            runtime_status=CuratedAppPublicRuntimeStatus.GRANT_CONTRACT_READY,
        )
    )
    active = public_apps_api._build_exam_converter_capability_metadata(
        capability=CuratedAppPublicCapability(
            scope="exam_converter",
            profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
            runtime_status=CuratedAppPublicRuntimeStatus.ACTIVE,
        )
    )

    assert contract_only.runtime_status is CuratedAppPublicRuntimeStatus.CONTRACT_ONLY
    assert contract_only.action_affordances == []
    assert grant_ready.runtime_status is CuratedAppPublicRuntimeStatus.GRANT_CONTRACT_READY
    assert {affordance.enabled for affordance in grant_ready.action_affordances} == {False}
    assert active.runtime_status is CuratedAppPublicRuntimeStatus.ACTIVE
    assert {affordance.enabled for affordance in active.action_affordances} == {True}
