from typing import Literal

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.commands import (
    ChangeEmailCommand,
    ChangePasswordCommand,
    GetProfileCommand,
    UpdateAiSettingsCommand,
    UpdateProfileCommand,
)
from skriptoteket.domain.identity.models import User, UserProfile
from skriptoteket.protocols.identity import (
    ChangeEmailHandlerProtocol,
    ChangePasswordHandlerProtocol,
    GetProfileHandlerProtocol,
    UpdateAiSettingsHandlerProtocol,
    UpdateProfileHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    locale: str | None = None


class UpdateAiSettingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    remote_fallback_preference: Literal["unset", "allow", "deny"]


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
@inject
async def get_profile(
    handler: FromDishka[GetProfileHandlerProtocol],
    user: User = Depends(require_user_api),
) -> ProfileResponse:
    result = await handler.handle(GetProfileCommand(user_id=user.id))
    return ProfileResponse(user=result.user, profile=result.profile)


@router.patch("", response_model=ProfileResponse)
@inject
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
@inject
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
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
@inject
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
@inject
async def change_email(
    payload: ChangeEmailRequest,
    handler: FromDishka[ChangeEmailHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ChangeEmailResponse:
    result = await handler.handle(ChangeEmailCommand(user_id=user.id, new_email=payload.email))
    return ChangeEmailResponse(user=result.user)
