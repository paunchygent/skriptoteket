"""Request-scoped AI preference helpers for app-local profile state.

Purpose:
    Resolve editor AI consent and provider preferences from Skriptoteket
    UserProfile data instead of browser session rows.

Relationships:
    - Editor AI API routes use `require_app_ai_preferences` when constructing
      application-layer AI commands.
    - Profile continuation APIs reuse `load_ai_preferences_for_user` to return
      the app-local bootstrap continuation contract.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_projection_api


class AiPreferences(BaseModel):
    model_config = ConfigDict(frozen=True)
    allow_remote_fallback: bool | None = None
    inline_completion_provider: Literal["local", "external"] | None = None


async def load_ai_preferences_for_user(
    *,
    profiles: ProfileRepositoryProtocol,
    user_id: UUID,
) -> AiPreferences:
    profile = await profiles.get_by_user_id(user_id=user_id)
    if profile is None:
        return AiPreferences()
    return AiPreferences(
        allow_remote_fallback=profile.allow_remote_fallback,
        inline_completion_provider=profile.inline_completion_provider,
    )


async def require_app_ai_preferences(
    projection: HuleEduAppUserProjection = Depends(require_app_user_projection_api),
) -> AiPreferences:
    return AiPreferences(
        allow_remote_fallback=projection.profile.allow_remote_fallback,
        inline_completion_provider=projection.profile.inline_completion_provider,
    )
