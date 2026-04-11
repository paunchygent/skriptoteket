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

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.application.identity.commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    GetProfileCommand,
    UpdateAiSettingsCommand,
    UpdateProfileCommand,
)
from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User, UserProfile
from skriptoteket.protocols.identity import (
    ChangeEmailHandlerProtocol,
    ChangePasswordHandlerProtocol,
    GetProfileHandlerProtocol,
    UpdateAiSettingsHandlerProtocol,
    UpdateProfileHandlerProtocol,
)
from skriptoteket.web.api.v1.ai_policy import AiPolicyResponse, build_ai_policy
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.auth.huleedu_app_projection import require_huleedu_app_user_projection
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


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    current_password: str
    new_password: str


class ChangeEmailRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str


class ChangeEmailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    user: User


@router.get("", response_model=ProfileResponse)
async def get_profile(
    handler: FromDishka[GetProfileHandlerProtocol],
    user: User = Depends(require_user_api),
) -> ProfileResponse:
    result = await handler.handle(GetProfileCommand(user_id=user.id))
    return ProfileResponse(user=result.user, profile=result.profile)


@router.get("/app-continuation", response_model=ProfileAppContinuationResponse)
async def get_app_continuation(
    settings: FromDishka[Settings],
    projection: HuleEduAppUserProjection = Depends(require_huleedu_app_user_projection),
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
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
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
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateAiSettingsCommand(
            user_id=user.id,
            remote_fallback_preference=payload.remote_fallback_preference,
            inline_completion_provider_preference=payload.inline_completion_provider_preference,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    handler: FromDishka[ChangePasswordHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(
        ChangePasswordCommand(
            user_id=user.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    )
    return None


@router.patch("/email", response_model=ChangeEmailResponse)
async def change_email(
    payload: ChangeEmailRequest,
    handler: FromDishka[ChangeEmailHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ChangeEmailResponse:
    result = await handler.handle(ChangeEmailCommand(user_id=user.id, new_email=payload.email))
    return ChangeEmailResponse(user=result.user)
