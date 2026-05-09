"""Profile and app-local continuation routes for the SPA API.

Purpose:
    Expose user profile mutations and the Skriptoteket-owned app continuation
    payload that follows HuleEdu shared-session bootstrap.

Relationships:
    - Profile mutations delegate to identity application handlers.
    - The continuation endpoint combines runtime AI policy with profile AI
      preferences without answering browser-auth identity questions.
"""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.application.identity.commands import (
    GetProfileCommand,
    UpdateAiSettingsCommand,
    UpdateClassroomPlannerSettingsCommand,
    UpdateProfileCommand,
)
from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User, UserProfile
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    UpdateAiSettingsHandlerProtocol,
    UpdateClassroomPlannerSettingsHandlerProtocol,
    UpdateProfileHandlerProtocol,
)
from skriptoteket.web.api.v1.ai_policy import AiPolicyResponse, build_ai_policy
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_user_api,
    require_app_user_projection_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    user: User
    profile: UserProfile


class ProfileAppContinuationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    local_user: User
    profile: UserProfile
    ai_policy: AiPolicyResponse
    allow_remote_fallback: bool | None = None
    inline_completion_provider: Literal["local", "external"] | None = None


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    locale: str | None = None


class UpdateAiSettingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    remote_fallback_preference: Literal["unset", "allow", "deny"] | None = None
    inline_completion_provider_preference: Literal["unset", "local", "external"] | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateAiSettingsRequest":
        if (
            self.remote_fallback_preference is None
            and self.inline_completion_provider_preference is None
        ):
            raise ValueError("At least one AI setting is required")
        return self


class UpdateClassroomPlannerSettingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    smart_enabled: bool | None = None
    use_history: bool | None = None
    grouping_seating_distance_enabled: bool | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateClassroomPlannerSettingsRequest":
        if (
            self.smart_enabled is None
            and self.use_history is None
            and self.grouping_seating_distance_enabled is None
        ):
            raise ValueError("At least one classroom planner setting is required")
        return self


@router.get("", response_model=ProfileResponse)
async def get_profile(
    handler: FromDishka[GetProfileHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(GetProfileCommand(user_id=user.id))
    return ProfileResponse(user=result.user, profile=result.profile)


@router.get("/app-continuation", response_model=ProfileAppContinuationResponse)
async def get_app_continuation(
    settings: FromDishka[Settings],
    projection: HuleEduAppUserProjection = Depends(require_app_user_projection_api),
) -> ProfileAppContinuationResponse:
    return ProfileAppContinuationResponse(
        local_user=projection.user,
        profile=projection.profile,
        ai_policy=build_ai_policy(settings),
        allow_remote_fallback=projection.profile.allow_remote_fallback,
        inline_completion_provider=projection.profile.inline_completion_provider,
    )


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    handler: FromDishka[UpdateProfileHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateProfileCommand(
            user_id=user.id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            display_name=payload.display_name,
            locale=payload.locale,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.patch("/ai-settings", response_model=ProfileResponse)
async def update_ai_settings(
    payload: UpdateAiSettingsRequest,
    handler: FromDishka[UpdateAiSettingsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateAiSettingsCommand(
            user_id=user.id,
            remote_fallback_preference=payload.remote_fallback_preference,
            inline_completion_provider_preference=payload.inline_completion_provider_preference,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.patch("/classroom-planner-settings", response_model=ProfileResponse)
async def update_classroom_planner_settings(
    payload: UpdateClassroomPlannerSettingsRequest,
    handler: FromDishka[UpdateClassroomPlannerSettingsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateClassroomPlannerSettingsCommand(
            user_id=user.id,
            smart_enabled=payload.smart_enabled,
            use_history=payload.use_history,
            grouping_seating_distance_enabled=payload.grouping_seating_distance_enabled,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)
