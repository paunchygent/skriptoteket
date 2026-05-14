"""Curated-app model tests for public capability boundaries."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)


def _make_app(
    *,
    public_capabilities: list[CuratedAppPublicCapability] | None = None,
) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id="documents.conversion_hub",
        tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Konvertera dokument",
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=public_capabilities or [],
        placements=[
            CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
        ],
    )


def test_scoped_public_capability_does_not_make_whole_app_public() -> None:
    app = _make_app(
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
            )
        ],
    )

    assert app.supports_public_access is False
    assert app.supports_public_capability(scope="exam_converter") is True
    assert app.supports_public_capability(scope="general_conversion") is False
    assert app.get_public_capability(scope="exam_converter") is not None


def test_public_capability_rejects_authenticated_only_profile() -> None:
    with pytest.raises(ValueError, match="public capability profile"):
        CuratedAppPublicCapability(
            scope="exam_converter",
            profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        )


def test_public_capability_defaults_to_contract_only_runtime_status() -> None:
    capability = CuratedAppPublicCapability(
        scope="exam_converter",
        profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
    )

    assert capability.runtime_status is CuratedAppPublicRuntimeStatus.CONTRACT_ONLY


def test_public_capability_accepts_grant_contract_ready_runtime_status() -> None:
    capability = CuratedAppPublicCapability(
        scope="exam_converter",
        profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
        runtime_status=CuratedAppPublicRuntimeStatus.GRANT_CONTRACT_READY,
    )

    assert capability.runtime_status is CuratedAppPublicRuntimeStatus.GRANT_CONTRACT_READY


def test_curated_app_rejects_duplicate_public_capability_scopes() -> None:
    capability = CuratedAppPublicCapability(
        scope="exam_converter",
        profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
    )

    with pytest.raises(ValueError, match="public capability scopes must be unique"):
        _make_app(public_capabilities=[capability, capability])
