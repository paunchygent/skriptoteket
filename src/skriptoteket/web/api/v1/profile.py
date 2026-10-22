"""Profile and app-local continuation routes for the SPA API.

Purpose:
    Expose user profile mutations and the Skriptoteket-owned app continuation
    payload that follows HuleEdu shared-session bootstrap.

Relationships:
    - Profile mutations delegate to identity application handlers.
    - The continuation endpoint returns the local user and profile without
      answering browser-auth identity questions.
"""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from skriptoteket.application.identity.commands import (
    GetProfileCommand,
    UpdateClassroomPlannerSettingsCommand,
    UpdateExamCoursesCommand,
    UpdateExamListOrderingCommand,
    UpdateProfileCommand,
)
from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import SchoolForm
from skriptoteket.domain.identity.models import (
    User,
    UserProfile,
    normalize_classroom_planner_tutorial_seen_sections,
)
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    UpdateClassroomPlannerSettingsHandlerProtocol,
    UpdateExamCoursesHandlerProtocol,
    UpdateExamListOrderingHandlerProtocol,
    UpdateProfileHandlerProtocol,
)
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


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    locale: str | None = None


class UpdateClassroomPlannerSettingsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    smart_enabled: bool | None = None
    use_history: bool | None = None
    grouping_seating_distance_enabled: bool | None = None
    # Replace semantics: the client sends the full list of seen tutorial sections.
    tutorial_seen_sections: list[str] | None = None

    @field_validator("tutorial_seen_sections")
    @classmethod
    def validate_tutorial_seen_sections(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_classroom_planner_tutorial_seen_sections(value)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateClassroomPlannerSettingsRequest":
        if (
            self.smart_enabled is None
            and self.use_history is None
            and self.grouping_seating_distance_enabled is None
            and self.tutorial_seen_sections is None
        ):
            raise ValueError("At least one classroom planner setting is required")
        return self


class UpdateExamListOrderingRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ordering: Literal["course", "newest"]


class UpdateExamCoursesRequest(BaseModel):
    """Replace semantics: the client sends the full registered course state."""

    model_config = ConfigDict(frozen=True)

    school_forms: list[SchoolForm]
    course_keys: list[str]


@router.get("", response_model=ProfileResponse)
async def get_profile(
    handler: FromDishka[GetProfileHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(GetProfileCommand(user_id=user.id))
    return ProfileResponse(user=result.user, profile=result.profile)


@router.get("/app-continuation", response_model=ProfileAppContinuationResponse)
async def get_app_continuation(
    projection: HuleEduAppUserProjection = Depends(require_app_user_projection_api),
) -> ProfileAppContinuationResponse:
    return ProfileAppContinuationResponse(
        local_user=projection.user,
        profile=projection.profile,
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
            tutorial_seen_sections=payload.tutorial_seen_sections,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.patch("/exam-list-ordering", response_model=ProfileResponse)
async def update_exam_list_ordering(
    payload: UpdateExamListOrderingRequest,
    handler: FromDishka[UpdateExamListOrderingHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateExamListOrderingCommand(user_id=user.id, ordering=payload.ordering)
    )
    return ProfileResponse(user=result.user, profile=result.profile)


@router.patch("/exam-courses", response_model=ProfileResponse)
async def update_exam_courses(
    payload: UpdateExamCoursesRequest,
    handler: FromDishka[UpdateExamCoursesHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ProfileResponse:
    result = await handler.handle(
        UpdateExamCoursesCommand(
            user_id=user.id,
            school_forms=payload.school_forms,
            course_keys=payload.course_keys,
        )
    )
    return ProfileResponse(user=result.user, profile=result.profile)
