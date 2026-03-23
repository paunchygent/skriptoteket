"""Unit coverage for the Flunk-Out Frenzy bootstrap handler.

This module verifies that the minimal game bootstrap contract is derived from
registry metadata and keeps the initial feature-flag surface intentionally
small.
"""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.flunk_out_frenzy import (
    FLUNK_OUT_FRENZY_RULESET_ID,
    GetFlunkOutFrenzyBootstrapHandler,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role


def _make_app() -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id="games.flunk_out_frenzy",
        tool_id=curated_app_tool_id(app_id="games.flunk_out_frenzy"),
        app_version="app:0.2.0",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Flunk-Out Frenzy",
        summary="Local browser pinball with future official high scores.",
        min_role=Role.USER,
        placements=[
            CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
        ],
    )


@pytest.mark.asyncio
async def test_bootstrap_handler_returns_minimal_bootstrap_payload() -> None:
    handler = GetFlunkOutFrenzyBootstrapHandler()

    result = await handler.handle(app=_make_app())

    assert result.app_id == "games.flunk_out_frenzy"
    assert result.title == "Flunk-Out Frenzy"
    assert result.app_version == "app:0.2.0"
    assert result.ruleset_id == FLUNK_OUT_FRENZY_RULESET_ID
    assert result.feature_flags.audio_enabled is True
    assert result.feature_flags.replay_capture_enabled is False
    assert result.feature_flags.score_submission_enabled is False
