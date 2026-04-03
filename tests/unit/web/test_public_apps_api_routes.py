"""Route tests for public curated-app bootstrap lookups."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
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
