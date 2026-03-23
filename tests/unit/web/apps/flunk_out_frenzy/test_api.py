"""Route tests for the Flunk-Out Frenzy bootstrap API.

This module verifies that the bespoke game bootstrap endpoint delegates to the
application handler and applies the curated-app access gate at the web
boundary.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.curated_apps.flunk_out_frenzy import (
    FLUNK_OUT_FRENZY_RULESET_ID,
    FlunkOutFrenzyBootstrapResult,
    FlunkOutFrenzyFeatureFlags,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.flunk_out_frenzy import FlunkOutFrenzyBootstrapHandlerProtocol
from skriptoteket.web.api.v1 import apps_flunk_out_frenzy as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _make_app(*, min_role: Role = Role.USER) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id="games.flunk_out_frenzy",
        tool_id=curated_app_tool_id(app_id="games.flunk_out_frenzy"),
        app_version="app:0.2.0",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Flunk-Out Frenzy",
        summary="Local browser pinball with future official high scores.",
        min_role=min_role,
        placements=[
            CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
        ],
    )


def _make_bootstrap() -> FlunkOutFrenzyBootstrapResult:
    return FlunkOutFrenzyBootstrapResult(
        app_id="games.flunk_out_frenzy",
        title="Flunk-Out Frenzy",
        summary="Local browser pinball with future official high scores.",
        app_version="app:0.2.0",
        ruleset_id=FLUNK_OUT_FRENZY_RULESET_ID,
        feature_flags=FlunkOutFrenzyFeatureFlags(
            audio_enabled=True,
            replay_capture_enabled=False,
            score_submission_enabled=False,
        ),
    )


@pytest.mark.asyncio
async def test_get_bootstrap_returns_handler_payload() -> None:
    app = _make_app()
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = app
    handler = AsyncMock(spec=FlunkOutFrenzyBootstrapHandlerProtocol)
    handler.handle.return_value = _make_bootstrap()

    result = await _unwrap_dishka(api.get_bootstrap)(
        registry=registry,
        handler=handler,
        user=make_user(role=Role.USER),
    )

    assert result.app_id == "games.flunk_out_frenzy"
    assert result.ruleset_id == FLUNK_OUT_FRENZY_RULESET_ID
    handler.handle.assert_awaited_once_with(app=app)


@pytest.mark.asyncio
async def test_get_bootstrap_raises_not_found_when_registry_entry_is_missing() -> None:
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = None
    handler = AsyncMock(spec=FlunkOutFrenzyBootstrapHandlerProtocol)

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(api.get_bootstrap)(
            registry=registry,
            handler=handler,
            user=make_user(role=Role.USER),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    handler.handle.assert_not_called()


@pytest.mark.asyncio
async def test_get_bootstrap_enforces_role_gate() -> None:
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = _make_app(min_role=Role.ADMIN)
    handler = AsyncMock(spec=FlunkOutFrenzyBootstrapHandlerProtocol)

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(api.get_bootstrap)(
            registry=registry,
            handler=handler,
            user=make_user(role=Role.USER),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    handler.handle.assert_not_called()
