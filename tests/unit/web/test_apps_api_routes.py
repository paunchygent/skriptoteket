"""Route tests for generic curated app detail lookups."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1 import apps as apps_api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _make_app(
    *, app_id: str = "games.flunk_out_frenzy", min_role: Role = Role.USER
) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Flunk-Out Frenzy",
        summary="Local browser pinball with future official high scores.",
        min_role=min_role,
        placements=[
            CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
            CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt"),
        ],
    )


@pytest.mark.asyncio
async def test_get_app_by_id_returns_curated_app_detail() -> None:
    app = _make_app()
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    response = await _unwrap_dishka(apps_api.get_app_by_id)(
        app_id=app.app_id,
        registry=registry,
        user=make_user(role=Role.USER),
    )

    assert response.app_id == "games.flunk_out_frenzy"
    assert response.tool_id == curated_app_tool_id(app_id="games.flunk_out_frenzy")
    assert response.title == "Flunk-Out Frenzy"
    assert response.ui_mode is CuratedAppUiMode.BESPOKE_REQUIRED


@pytest.mark.asyncio
async def test_get_app_by_id_raises_not_found_for_unknown_app() -> None:
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = None

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(apps_api.get_app_by_id)(
            app_id="games.flunk_out_frenzy",
            registry=registry,
            user=make_user(role=Role.USER),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_app_by_id_enforces_role_gate() -> None:
    app = _make_app(app_id="games.admin_only", min_role=Role.ADMIN)
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(apps_api.get_app_by_id)(
            app_id=app.app_id,
            registry=registry,
            user=make_user(role=Role.USER),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
