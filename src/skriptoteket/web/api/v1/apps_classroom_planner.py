"""API endpoints for the Classroom Planner curated app (Klassrumskartan)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetBootstrapHandler,
    GetDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
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
    handler: FromDishka[GetBootstrapHandler],
    user: User = Depends(require_user_api),
) -> ClassroomPlannerBootstrapResponse:
    """Returns the initialization payload for the Classroom Planner."""
    payload = await handler.handle(owner_user_id=user.id)

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

    @model_validator(mode="after")
    def validate_unique_students(self) -> "CreateRosterRequest":
        ids = [s.id for s in self.students]
        if len(ids) != len(set(ids)):
            raise ValueError("Student IDs must be unique within a roster.")
        return self


class UpdateRosterRequest(CreateRosterRequest):
    """Alias for updating a roster."""

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

    @model_validator(mode="after")
    def validate_unique_seats(self) -> "CreateRoomTemplateRequest":
        ids = [s.id for s in self.seats]
        if len(ids) != len(set(ids)):
            raise ValueError("Seat IDs must be unique within a room template.")
        return self


class UpdateRoomTemplateRequest(CreateRoomTemplateRequest):
    """Alias for updating a room template."""

    pass


# Roster Endpoints


@router.get("/rosters", response_model=list[RosterDto])
@inject
async def list_rosters(
    handler: FromDishka[ListRostersHandler],
    user: User = Depends(require_user_api),
) -> list[RosterDto]:
    rosters = await handler.handle(owner_user_id=user.id)
    return [RosterDto.model_validate(r) for r in rosters]


@router.get("/rosters/{roster_id}", response_model=RosterDto)
@inject
async def get_roster(
    roster_id: UUID,
    handler: FromDishka[GetRosterHandler],
    user: User = Depends(require_user_api),
) -> RosterDto:
    roster = await handler.handle(roster_id=roster_id, owner_user_id=user.id)
    return RosterDto.model_validate(roster)


@router.post("/rosters", response_model=RosterDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_roster(
    request: CreateRosterRequest,
    handler: FromDishka[CreateRosterHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RosterDto:
    roster = await handler.handle(
        owner_user_id=user.id, name=request.name, students=request.students
    )
    return RosterDto.model_validate(roster)


@router.put("/rosters/{roster_id}", response_model=RosterDto)
@inject
async def update_roster(
    roster_id: UUID,
    request: UpdateRosterRequest,
    handler: FromDishka[UpdateRosterHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RosterDto:
    roster = await handler.handle(
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
    handler: FromDishka[DeleteRosterHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(roster_id=roster_id, owner_user_id=user.id)


# RoomTemplate Endpoints


@router.get("/templates", response_model=list[RoomTemplateDto])
@inject
async def list_templates(
    handler: FromDishka[ListRoomTemplatesHandler],
    user: User = Depends(require_user_api),
) -> list[RoomTemplateDto]:
    templates = await handler.handle(owner_user_id=user.id)
    return [RoomTemplateDto.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=RoomTemplateDto)
@inject
async def get_template(
    template_id: UUID,
    handler: FromDishka[GetRoomTemplateHandler],
    user: User = Depends(require_user_api),
) -> RoomTemplateDto:
    template = await handler.handle(template_id=template_id, owner_user_id=user.id)
    return RoomTemplateDto.model_validate(template)


@router.post("/templates", response_model=RoomTemplateDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_template(
    request: CreateRoomTemplateRequest,
    handler: FromDishka[CreateRoomTemplateHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RoomTemplateDto:
    template = await handler.handle(owner_user_id=user.id, name=request.name, seats=request.seats)
    return RoomTemplateDto.model_validate(template)


@router.put("/templates/{template_id}", response_model=RoomTemplateDto)
@inject
async def update_template(
    template_id: UUID,
    request: UpdateRoomTemplateRequest,
    handler: FromDishka[UpdateRoomTemplateHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RoomTemplateDto:
    template = await handler.handle(
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
    handler: FromDishka[DeleteRoomTemplateHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(template_id=template_id, owner_user_id=user.id)


# PlanDraft DTOs


class GroupAssignmentDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)
    student_id: str
    group_id: str


class SeatAssignmentDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)
    student_id: str
    seat_id: str


class PlanDraftDto(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    revision: int
    group_count: int
    group_assignments: list[GroupAssignmentDto]
    seat_assignments: list[SeatAssignmentDto]


class CreatePlanDraftRequest(BaseModel):
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    group_assignments: list[GroupAssignmentDto] = Field(default_factory=list)
    seat_assignments: list[SeatAssignmentDto] = Field(default_factory=list)


class UpdatePlanDraftRequest(BaseModel):
    expected_revision: int | None = None
    group_count: int | None = None
    group_assignments: list[GroupAssignmentDto] | None = None
    seat_assignments: list[SeatAssignmentDto] | None = None


# PlanDraft Endpoints


@router.post("/drafts", response_model=PlanDraftDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_draft(
    request: CreatePlanDraftRequest,
    handler: FromDishka[CreateDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        template_id=request.template_id,
        lesson_mode_id=request.lesson_mode_id,
        group_assignments=[
            GroupAssignment(student_id=ga.student_id, group_id=ga.group_id)
            for ga in request.group_assignments
        ],
        seat_assignments=[
            SeatAssignment(student_id=sa.student_id, seat_id=sa.seat_id)
            for sa in request.seat_assignments
        ],
    )
    return PlanDraftDto.model_validate(draft)


@router.get("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def get_draft(
    draft_id: UUID,
    handler: FromDishka[GetDraftHandler],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    draft = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return PlanDraftDto.model_validate(draft)


@router.patch("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def update_draft(
    draft_id: UUID,
    request: UpdatePlanDraftRequest,
    handler: FromDishka[PatchDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=request.expected_revision,
        group_count=request.group_count,
        group_assignments=[
            GroupAssignment(student_id=ga.student_id, group_id=ga.group_id)
            for ga in request.group_assignments
        ]
        if request.group_assignments is not None
        else None,
        seat_assignments=[
            SeatAssignment(student_id=sa.student_id, seat_id=sa.seat_id)
            for sa in request.seat_assignments
        ]
        if request.seat_assignments is not None
        else None,
    )
    return PlanDraftDto.model_validate(draft)
