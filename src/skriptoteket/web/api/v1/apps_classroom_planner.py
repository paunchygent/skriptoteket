"""API endpoints for the Classroom Planner curated app (Klassrumskartan)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.apps.classroom_planner.services import (
    ClassroomPlannerBootstrapService,
    ClassroomPlannerService,
)
from skriptoteket.domain.apps.classroom_planner.models import Seat, Student
from skriptoteket.domain.identity.models import User
from skriptoteket.web.auth.api_dependencies import require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio", tags=["apps", "classroom-planner"]
)


class LessonModePresetDto(BaseModel):
    """DTO for a lesson mode preset."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str


class ClassroomPlannerBootstrapResponse(BaseModel):
    """Response payload for app initialization."""

    model_config = ConfigDict(frozen=True)

    lesson_modes: list[LessonModePresetDto]
    feature_flags: dict[str, bool]


@router.get("/bootstrap", response_model=ClassroomPlannerBootstrapResponse)
@inject
async def get_bootstrap(
    service: FromDishka[ClassroomPlannerBootstrapService],
    user: User = Depends(require_user_api),
) -> ClassroomPlannerBootstrapResponse:
    """Returns the initialization payload for the Classroom Planner."""
    payload = await service.get_bootstrap_payload(owner_user_id=user.id)

    return ClassroomPlannerBootstrapResponse(
        lesson_modes=[LessonModePresetDto(id=m.id, name=m.name) for m in payload.lesson_modes],
        feature_flags=payload.feature_flags,
    )


# Roster DTOs


class RosterDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    students: list[Student]


class CreateRosterRequest(BaseModel):
    name: str
    students: list[Student]


class UpdateRosterRequest(CreateRosterRequest):
    """Alias for updating a roster (F4)."""

    pass


# RoomTemplate DTOs


class RoomTemplateDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    seats: list[Seat]


class CreateRoomTemplateRequest(BaseModel):
    name: str
    seats: list[Seat]


class UpdateRoomTemplateRequest(CreateRoomTemplateRequest):
    """Alias for updating a room template (F4)."""

    pass


# Roster Endpoints


@router.get("/rosters", response_model=list[RosterDto])
@inject
async def list_rosters(
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> list[RosterDto]:
    rosters = await service.list_rosters(owner_user_id=user.id)
    return [RosterDto.model_validate(r) for r in rosters]


@router.get("/rosters/{roster_id}", response_model=RosterDto)
@inject
async def get_roster(
    roster_id: UUID,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RosterDto:
    roster = await service.get_roster(roster_id=roster_id, owner_user_id=user.id)
    return RosterDto.model_validate(roster)


@router.post("/rosters", response_model=RosterDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_roster(
    request: CreateRosterRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RosterDto:
    roster = await service.create_roster(
        owner_user_id=user.id, name=request.name, students=request.students
    )
    return RosterDto.model_validate(roster)


@router.put("/rosters/{roster_id}", response_model=RosterDto)
@inject
async def update_roster(
    roster_id: UUID,
    request: UpdateRosterRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RosterDto:
    roster = await service.update_roster(
        roster_id=roster_id,
        owner_user_id=user.id,
        name=request.name,
        students=request.students,
    )
    return RosterDto.model_validate(roster)


@router.delete("/rosters/{roster_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_roster(
    roster_id: UUID,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> None:
    await service.delete_roster(roster_id=roster_id, owner_user_id=user.id)


# RoomTemplate Endpoints


@router.get("/templates", response_model=list[RoomTemplateDto])
@inject
async def list_templates(
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> list[RoomTemplateDto]:
    templates = await service.list_templates(owner_user_id=user.id)
    return [RoomTemplateDto.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=RoomTemplateDto)
@inject
async def get_template(
    template_id: UUID,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RoomTemplateDto:
    template = await service.get_template(template_id=template_id, owner_user_id=user.id)
    return RoomTemplateDto.model_validate(template)


@router.post("/templates", response_model=RoomTemplateDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_template(
    request: CreateRoomTemplateRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RoomTemplateDto:
    template = await service.create_template(
        owner_user_id=user.id, name=request.name, seats=request.seats
    )
    return RoomTemplateDto.model_validate(template)


@router.put("/templates/{template_id}", response_model=RoomTemplateDto)
@inject
async def update_template(
    template_id: UUID,
    request: UpdateRoomTemplateRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> RoomTemplateDto:
    template = await service.update_template(
        template_id=template_id,
        owner_user_id=user.id,
        name=request.name,
        seats=request.seats,
    )
    return RoomTemplateDto.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_template(
    template_id: UUID,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> None:
    await service.delete_template(template_id=template_id, owner_user_id=user.id)


# PlanDraft DTOs


class PlanDraftDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    group_assignments: dict[str, str | None]
    seat_assignments: dict[str, str | None]


class CreatePlanDraftRequest(BaseModel):
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    group_assignments: dict[str, str | None] = Field(default_factory=dict)
    seat_assignments: dict[str, str | None] = Field(default_factory=dict)


class UpdatePlanDraftRequest(BaseModel):
    group_assignments: dict[str, str | None] | None = None
    seat_assignments: dict[str, str | None] | None = None


# PlanDraft Endpoints


@router.post("/drafts", response_model=PlanDraftDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_draft(
    request: CreatePlanDraftRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    draft = await service.create_draft(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        template_id=request.template_id,
        lesson_mode_id=request.lesson_mode_id,
        group_assignments=request.group_assignments,
        seat_assignments=request.seat_assignments,
    )
    return PlanDraftDto.model_validate(draft)


@router.get("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def get_draft(
    draft_id: UUID,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    draft = await service.get_draft(draft_id=draft_id, owner_user_id=user.id)
    return PlanDraftDto.model_validate(draft)


@router.patch("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def update_draft(
    draft_id: UUID,
    request: UpdatePlanDraftRequest,
    service: FromDishka[ClassroomPlannerService],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    draft = await service.update_draft(
        draft_id=draft_id,
        owner_user_id=user.id,
        group_assignments=request.group_assignments,
        seat_assignments=request.seat_assignments,
    )
    return PlanDraftDto.model_validate(draft)
