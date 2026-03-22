"""API endpoints for the Classroom Planner curated app.

This router exposes the bespoke classroom-planner contract used by the SPA. It
keeps reusable roster and room assets separate from draft-scoped workspace
state and only publishes the current fundamentals workflow for grouping,
seating, and student planning notes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetClassWorkspaceSummaryHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetResumableDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    UndoDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    GroupAssignment,
    PlanDraftKind,
    ResumablePlanDraft,
    RoomFixture,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
    StudentPlanningMeta,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import (
    PlanDraftDto,
    serialize_plan_draft,
)
from skriptoteket.web.api.v1.apps_classroom_planner_summary import (
    ClassWorkspaceSummaryDto,
    serialize_class_workspace_summary,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio", tags=["apps", "classroom-planner"]
)


def _assert_unique(values: list[str], *, label: str) -> None:
    """Reject duplicate identifiers in one request collection."""

    if len(values) != len(set(values)):
        raise ValueError(f"{label} IDs must be unique.")


class StudentDto(BaseModel):
    """Serialize a roster student."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    display_name: str


class RoomFixtureDto(BaseModel):
    """Serialize a room fixture."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    type: str
    x: int
    y: int
    width: int
    height: int
    label: str | None = None


class RosterDto(BaseModel):
    """Serialize a reusable roster."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    students: list[StudentDto]


class CreateRosterRequest(BaseModel):
    """Deserialize a roster create or update payload."""

    name: str
    students: list[Student]

    @model_validator(mode="after")
    def validate_unique_students(self) -> "CreateRosterRequest":
        _assert_unique([student.id for student in self.students], label="Student")
        return self


class UpdateRosterRequest(CreateRosterRequest):
    """Alias for roster updates."""


class SeatDto(BaseModel):
    """Serialize a room seat."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class RoomTemplateDto(BaseModel):
    """Serialize a reusable room template."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    seats: list[SeatDto]
    fixtures: list[RoomFixtureDto]


class CreateRoomTemplateRequest(BaseModel):
    """Deserialize a room template create or update payload."""

    name: str
    seats: list[Seat]
    fixtures: list[RoomFixture] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_items(self) -> "CreateRoomTemplateRequest":
        _assert_unique([seat.id for seat in self.seats], label="Seat")
        _assert_unique([fixture.id for fixture in self.fixtures], label="Fixture")
        return self


class UpdateRoomTemplateRequest(CreateRoomTemplateRequest):
    """Alias for room template updates."""


class DraftGroupDto(BaseModel):
    """Serialize a draft-scoped group."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str
    sort_order: int
    name_is_custom: bool = False


class GroupAssignmentDto(BaseModel):
    """Serialize one student-to-group assignment."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    group_id: str


class SeatAssignmentDto(BaseModel):
    """Serialize one student-to-seat assignment."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    seat_id: str


class StudentPlanningMetaDto(BaseModel):
    """Serialize teacher-only student planning metadata."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    teacher_proximity: int = 0
    stability_preference: int = 0
    preferred_zone: str | None = None
    avoid_zone: str | None = None
    notes: str | None = None


class ResumablePlanDraftDto(BaseModel):
    """Serialize the latest resumable draft CTA payload."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraftDto
    roster_name: str
    template_name: str | None = None


class GroupingHistoryStatusDto(BaseModel):
    """Serialize the undo/redo availability for a grouping draft."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    can_undo: bool
    can_redo: bool


class DraftWorkspaceResponse(BaseModel):
    """Serialize the hydrated fundamentals planner workspace."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraftDto
    roster: RosterDto
    template: RoomTemplateDto | None = None
    groups: list[DraftGroupDto]
    group_assignments: list[GroupAssignmentDto]
    seat_assignments: list[SeatAssignmentDto]
    student_planning_meta: list[StudentPlanningMetaDto]
    history_status: GroupingHistoryStatusDto


class ResolvePlanDraftRequest(BaseModel):
    """Deserialize the landing-page resolve request."""

    roster_id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None


class UpdatePlanDraftRequest(BaseModel):
    """Deserialize mutable draft workspace patches."""

    expected_revision: int | None = None
    groups: list[DraftGroupDto] | None = None
    group_assignments: list[GroupAssignmentDto] | None = None
    seat_assignments: list[SeatAssignmentDto] | None = None
    student_planning_meta: list[StudentPlanningMetaDto] | None = None

    @model_validator(mode="after")
    def validate_unique_collections(self) -> "UpdatePlanDraftRequest":
        if self.groups is not None:
            _assert_unique([group.id for group in self.groups], label="Group")
        if self.student_planning_meta is not None:
            _assert_unique(
                [meta.student_id for meta in self.student_planning_meta], label="Student metadata"
            )
        if self.group_assignments is not None:
            _assert_unique(
                [assignment.student_id for assignment in self.group_assignments],
                label="Group assignment student",
            )
        if self.seat_assignments is not None:
            _assert_unique(
                [assignment.student_id for assignment in self.seat_assignments],
                label="Seat assignment student",
            )
            _assert_unique(
                [assignment.seat_id for assignment in self.seat_assignments],
                label="Seat assignment seat",
            )
        return self


def _serialize_roster(roster: Roster) -> RosterDto:
    """Map a roster aggregate to the public API response."""

    return RosterDto(
        id=roster.id,
        name=roster.name,
        students=[StudentDto.model_validate(student) for student in roster.students],
    )


def _serialize_template(template: RoomTemplate) -> RoomTemplateDto:
    """Map a room template aggregate to the public API response."""

    return RoomTemplateDto(
        id=template.id,
        name=template.name,
        seats=[SeatDto.model_validate(seat) for seat in template.seats],
        fixtures=[RoomFixtureDto.model_validate(fixture) for fixture in template.fixtures],
    )


def _serialize_resumable_plan_draft(resumable: ResumablePlanDraft) -> ResumablePlanDraftDto:
    """Map the resumable draft aggregate to the landing-page CTA response."""

    return ResumablePlanDraftDto(
        draft=serialize_plan_draft(resumable.draft),
        roster_name=resumable.roster_name,
        template_name=resumable.template_name,
    )


def _serialize_workspace(workspace: ClassroomPlannerWorkspace) -> DraftWorkspaceResponse:
    """Map the hydrated planner workspace to the public API response."""

    return DraftWorkspaceResponse(
        draft=serialize_plan_draft(workspace.draft),
        roster=_serialize_roster(workspace.roster),
        template=_serialize_template(workspace.template) if workspace.template else None,
        groups=[DraftGroupDto.model_validate(group) for group in workspace.groups],
        group_assignments=[
            GroupAssignmentDto.model_validate(assignment)
            for assignment in workspace.group_assignments
        ],
        seat_assignments=[
            SeatAssignmentDto.model_validate(assignment)
            for assignment in workspace.seat_assignments
        ],
        student_planning_meta=[
            StudentPlanningMetaDto.model_validate(meta) for meta in workspace.student_planning_meta
        ],
        history_status=GroupingHistoryStatusDto.model_validate(workspace.history_status),
    )


@router.post("/drafts/{draft_id}/undo", response_model=DraftWorkspaceResponse)
@inject
async def undo_draft(
    draft_id: UUID,
    handler: FromDishka[UndoDraftHandler],
    rosters: FromDishka[RosterRepositoryProtocol],
    templates: FromDishka[RoomTemplateRepositoryProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> DraftWorkspaceResponse:
    workspace = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return _serialize_workspace(
        ClassroomPlannerWorkspace(
            draft=workspace.draft,
            roster=await rosters.get_by_id(roster_id=workspace.draft.roster_id),
            template=await templates.get_by_id(template_id=workspace.draft.template_id)
            if workspace.draft.template_id
            else None,
            groups=workspace.groups,
            group_assignments=workspace.group_assignments,
            seat_assignments=workspace.seat_assignments,
            student_planning_meta=workspace.student_planning_meta,
            history_status=workspace.history_status,
        )
    )


@router.post("/drafts/{draft_id}/redo", response_model=DraftWorkspaceResponse)
@inject
async def redo_draft(
    draft_id: UUID,
    handler: FromDishka[RedoDraftHandler],
    rosters: FromDishka[RosterRepositoryProtocol],
    templates: FromDishka[RoomTemplateRepositoryProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> DraftWorkspaceResponse:
    workspace = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return _serialize_workspace(
        ClassroomPlannerWorkspace(
            draft=workspace.draft,
            roster=await rosters.get_by_id(roster_id=workspace.draft.roster_id),
            template=await templates.get_by_id(template_id=workspace.draft.template_id)
            if workspace.draft.template_id
            else None,
            groups=workspace.groups,
            group_assignments=workspace.group_assignments,
            seat_assignments=workspace.seat_assignments,
            student_planning_meta=workspace.student_planning_meta,
            history_status=workspace.history_status,
        )
    )


@router.get("/rosters", response_model=list[RosterDto])
@inject
async def list_rosters(
    handler: FromDishka[ListRostersHandler],
    user: User = Depends(require_user_api),
) -> list[RosterDto]:
    rosters = await handler.handle(owner_user_id=user.id)
    return [_serialize_roster(roster) for roster in rosters]


@router.get("/rosters/{roster_id}", response_model=RosterDto)
@inject
async def get_roster(
    roster_id: UUID,
    handler: FromDishka[GetRosterHandler],
    user: User = Depends(require_user_api),
) -> RosterDto:
    return _serialize_roster(await handler.handle(roster_id=roster_id, owner_user_id=user.id))


@router.get("/rosters/{roster_id}/workspace-summary", response_model=ClassWorkspaceSummaryDto)
@inject
async def get_class_workspace_summary(
    roster_id: UUID,
    handler: FromDishka[GetClassWorkspaceSummaryHandler],
    user: User = Depends(require_user_api),
) -> ClassWorkspaceSummaryDto:
    return serialize_class_workspace_summary(
        await handler.handle(roster_id=roster_id, owner_user_id=user.id)
    )


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
    return _serialize_roster(roster)


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
    return _serialize_roster(roster)


@router.delete("/rosters/{roster_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_roster(
    roster_id: UUID,
    handler: FromDishka[DeleteRosterHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(roster_id=roster_id, owner_user_id=user.id)


@router.get("/templates", response_model=list[RoomTemplateDto])
@inject
async def list_templates(
    handler: FromDishka[ListRoomTemplatesHandler],
    user: User = Depends(require_user_api),
) -> list[RoomTemplateDto]:
    templates = await handler.handle(owner_user_id=user.id)
    return [_serialize_template(template) for template in templates]


@router.get("/templates/{template_id}", response_model=RoomTemplateDto)
@inject
async def get_template(
    template_id: UUID,
    handler: FromDishka[GetRoomTemplateHandler],
    user: User = Depends(require_user_api),
) -> RoomTemplateDto:
    return _serialize_template(await handler.handle(template_id=template_id, owner_user_id=user.id))


@router.post("/templates", response_model=RoomTemplateDto, status_code=status.HTTP_201_CREATED)
@inject
async def create_template(
    request: CreateRoomTemplateRequest,
    handler: FromDishka[CreateRoomTemplateHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RoomTemplateDto:
    template = await handler.handle(
        owner_user_id=user.id,
        name=request.name,
        seats=request.seats,
        fixtures=request.fixtures,
    )
    return _serialize_template(template)


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
        fixtures=request.fixtures,
    )
    return _serialize_template(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_template(
    template_id: UUID,
    handler: FromDishka[DeleteRoomTemplateHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(template_id=template_id, owner_user_id=user.id)


@router.post("/drafts/resolve", response_model=PlanDraftDto)
@inject
async def resolve_draft(
    request: ResolvePlanDraftRequest,
    handler: FromDishka[ResolveDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        draft_kind=request.draft_kind,
        template_id=request.template_id,
    )
    return serialize_plan_draft(draft)


@router.post("/drafts/{draft_id}/abandon", response_model=PlanDraftDto)
@inject
async def abandon_draft(
    draft_id: UUID,
    handler: FromDishka[AbandonDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    return serialize_plan_draft(await handler.handle(draft_id=draft_id, owner_user_id=user.id))


@router.get("/drafts/resumable", response_model=ResumablePlanDraftDto | None)
@inject
async def get_resumable_draft(
    handler: FromDishka[GetResumableDraftHandler],
    user: User = Depends(require_user_api),
) -> ResumablePlanDraftDto | None:
    resumable = await handler.handle(owner_user_id=user.id)
    if resumable is None:
        return None
    return _serialize_resumable_plan_draft(resumable)


@router.get("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def get_draft(
    draft_id: UUID,
    handler: FromDishka[GetDraftHandler],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    return serialize_plan_draft(await handler.handle(draft_id=draft_id, owner_user_id=user.id))


@router.get("/drafts/{draft_id}/workspace", response_model=DraftWorkspaceResponse)
@inject
async def get_draft_workspace(
    draft_id: UUID,
    handler: FromDishka[GetDraftWorkspaceHandler],
    user: User = Depends(require_user_api),
) -> DraftWorkspaceResponse:
    workspace = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return _serialize_workspace(workspace)


@router.patch("/drafts/{draft_id}", response_model=DraftWorkspaceResponse)
@inject
async def update_draft(
    draft_id: UUID,
    request: UpdatePlanDraftRequest,
    handler: FromDishka[PatchDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> DraftWorkspaceResponse:
    workspace = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=request.expected_revision,
        groups=[DraftGroup.model_validate(group.model_dump()) for group in request.groups]
        if request.groups is not None
        else None,
        group_assignments=[
            GroupAssignment.model_validate(assignment.model_dump())
            for assignment in request.group_assignments
        ]
        if request.group_assignments is not None
        else None,
        seat_assignments=[
            SeatAssignment.model_validate(assignment.model_dump())
            for assignment in request.seat_assignments
        ]
        if request.seat_assignments is not None
        else None,
        student_planning_meta=[
            StudentPlanningMeta.model_validate(meta.model_dump())
            for meta in request.student_planning_meta
        ]
        if request.student_planning_meta is not None
        else None,
    )
    return _serialize_workspace(workspace)
