"""Minimal bootstrap contract for the Flunk-Out Frenzy curated app.

This module owns the first app-specific API contract for Flunk-Out Frenzy. It
turns the registry-backed curated-app metadata into a stable bootstrap payload
that the bespoke SPA shell can load before any local runtime work exists.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition

FLUNK_OUT_FRENZY_RULESET_ID = "flunk_out_frenzy.prototype_alpha.v1"


class FlunkOutFrenzyFeatureFlags(BaseModel):
    """Serialize the intentionally small app-level feature-flag surface."""

    model_config = ConfigDict(frozen=True)

    audio_enabled: bool
    replay_capture_enabled: bool
    score_submission_enabled: bool


class FlunkOutFrenzyBootstrapResult(BaseModel):
    """Serialize the initial game-shell bootstrap payload."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str
    app_version: str
    ruleset_id: str
    feature_flags: FlunkOutFrenzyFeatureFlags


class GetFlunkOutFrenzyBootstrapHandler:
    """Build the minimal Flunk-Out Frenzy bootstrap response."""

    async def handle(self, *, app: CuratedAppDefinition) -> FlunkOutFrenzyBootstrapResult:
        return FlunkOutFrenzyBootstrapResult(
            app_id=app.app_id,
            title=app.title,
            summary=app.summary,
            app_version=app.app_version,
            ruleset_id=FLUNK_OUT_FRENZY_RULESET_ID,
            feature_flags=FlunkOutFrenzyFeatureFlags(
                audio_enabled=True,
                replay_capture_enabled=False,
                score_submission_enabled=False,
            ),
        )
