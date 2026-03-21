"""API endpoints for the Classroom Planner curated app (Klassrumskartan).

This router exposes the bespoke classroom planner contract used by the SPA. It
keeps reusable roster/room assets separate from draft-scoped workspace state,
and provides dedicated endpoints for validation, suggestions, randomization,
and immutable snapshot finalization.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.classroom_planner import (
    ApplySuggestionHandler,
    CreateDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    FinalizeDraftHandler,
    GenerateSuggestionsHandler,
    GetBootstrapHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    GetSnapshotHandler,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    ListSnapshotsHandler,
    PatchDraftHandler,
    RandomizeDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
    ValidateDraftHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    GroupAssignment,
    PairConstraint,
    PlanDraft,
    PlanningProfile,
    RoomFixture,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
    StudentPlanningMeta,
    SuggestionList,
    ValidationResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio", tags=["apps", "classroom-planner"]
)


def _assert_unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} IDs must be unique.")


class LessonModePresetDto(BaseModel):
    """Serialize a lesson mode preset."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str


class ClassroomPlannerBootstrapResponse(BaseModel):
    """Serialize planner bootstrap metadata."""

    model_config = ConfigDict(frozen=True)

    lesson_modes: list[LessonModePresetDto]
    feature_flags: dict[str, bool]


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
    """Deserialize a roster create/update payload."""

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
    """Deserialize a room template create/update payload."""

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
    independent_focus_support: int = 0
    stability_preference: int = 0
    preferred_zone: str | None = None
    avoid_zone: str | None = None
    notes: str | None = None


class PairConstraintDto(BaseModel):
    """Serialize a draft-scoped pair constraint."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id_a: str
    student_id_b: str
    kind: str
    strength: int = 1


class PlanningProfileDto(BaseModel):
    """Serialize planning profile toggles and weights."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    profile_kind: str
    enable_student_meta: bool = True
    enable_pair_constraints: bool = True
    enable_zone_preferences: bool = True
    enable_history_rules: bool = False
    teacher_proximity_weight: int = 1
    focus_support_weight: int = 1
    stability_weight: int = 1
    balance_weight: int = 1
    rotation_weight: int = 1


class SuggestionEngineMetadataDto(BaseModel):
    """Serialize suggestion provenance metadata."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    suggestion_id: str
    profile_kind: str
    generated_at: datetime
    score_breakdown: dict[str, float]
    explanation_bullets: list[str]


class PlanDraftDto(BaseModel):
    """Serialize the mutable draft root."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    revision: int
    engine_metadata: SuggestionEngineMetadataDto | None = None


class DraftWorkspaceResponse(BaseModel):
    """Serialize the full hydrated planner workspace."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraftDto
    roster: RosterDto
    template: RoomTemplateDto
    groups: list[DraftGroupDto]
    group_assignments: list[GroupAssignmentDto]
    seat_assignments: list[SeatAssignmentDto]
    student_planning_meta: list[StudentPlanningMetaDto]
    pair_constraints: list[PairConstraintDto]
    planning_profile: PlanningProfileDto


class CreatePlanDraftRequest(BaseModel):
    """Deserialize new draft input."""

    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str


class UpdatePlanDraftRequest(BaseModel):
    """Deserialize mutable draft workspace patches."""

    expected_revision: int | None = None
    lesson_mode_id: str | None = None
    groups: list[DraftGroupDto] | None = None
    group_assignments: list[GroupAssignmentDto] | None = None
    seat_assignments: list[SeatAssignmentDto] | None = None
    student_planning_meta: list[StudentPlanningMetaDto] | None = None
    pair_constraints: list[PairConstraintDto] | None = None
    planning_profile: PlanningProfileDto | None = None

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
        if self.pair_constraints is not None:
            constraint_keys = [
                ":".join(
                    sorted([constraint.student_id_a, constraint.student_id_b]) + [constraint.kind]
                )
                for constraint in self.pair_constraints
            ]
            _assert_unique(constraint_keys, label="Pair constraint")
        return self


class RevisionRequest(BaseModel):
    """Deserialize expected-revision mutation requests."""

    expected_revision: int | None = None


class ValidationFindingDto(BaseModel):
    """Serialize one validation finding."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    severity: str
    code: str
    subject_ref: str | None = None
    message: str
    explanation: str


class ValidationResultResponse(BaseModel):
    """Serialize planner validation results."""

    model_config = ConfigDict(frozen=True)

    findings: list[ValidationFindingDto]


class SuggestionPlanDto(BaseModel):
    """Serialize one explainable suggestion."""

    model_config = ConfigDict(frozen=True)

    suggestion_id: str
    label: str
    profile_kind: str
    groups: list[DraftGroupDto]
    group_assignments: list[GroupAssignmentDto]
    seat_assignments: list[SeatAssignmentDto]
    score_breakdown: dict[str, float]
    findings: list[ValidationFindingDto]
    explanation_bullets: list[str]
    engine_metadata: SuggestionEngineMetadataDto


class SuggestionListResponse(BaseModel):
    """Serialize a batch of planner suggestions."""

    model_config = ConfigDict(frozen=True)

    suggestions: list[SuggestionPlanDto]


class ArrangementSnapshotDto(BaseModel):
    """Serialize an immutable arrangement snapshot."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    source_draft_id: UUID
    lesson_mode_id: str
    snapshot_schema_version: int
    payload: dict[str, object]
    created_at: datetime


def _serialize_roster(roster: Roster) -> RosterDto:
    return RosterDto(
        id=roster.id,
        name=roster.name,
        students=[StudentDto.model_validate(student) for student in roster.students],
    )


def _serialize_template(template: RoomTemplate) -> RoomTemplateDto:
    return RoomTemplateDto(
        id=template.id,
        name=template.name,
        seats=[SeatDto.model_validate(seat) for seat in template.seats],
        fixtures=[RoomFixtureDto.model_validate(fixture) for fixture in template.fixtures],
    )


def _serialize_plan_draft(draft: PlanDraft) -> PlanDraftDto:
    return PlanDraftDto.model_validate(draft)


def _serialize_workspace(workspace: ClassroomPlannerWorkspace) -> DraftWorkspaceResponse:
    return DraftWorkspaceResponse(
        draft=_serialize_plan_draft(workspace.draft),
        roster=_serialize_roster(workspace.roster),
        template=_serialize_template(workspace.template),
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
        pair_constraints=[
            PairConstraintDto.model_validate(constraint)
            for constraint in workspace.pair_constraints
        ],
        planning_profile=PlanningProfileDto.model_validate(workspace.planning_profile),
    )


def _serialize_validation(result: ValidationResult) -> ValidationResultResponse:
    return ValidationResultResponse(
        findings=[ValidationFindingDto.model_validate(finding) for finding in result.findings]
    )


def _serialize_suggestions(result: SuggestionList) -> SuggestionListResponse:
    return SuggestionListResponse(
        suggestions=[
            SuggestionPlanDto(
                suggestion_id=suggestion.suggestion_id,
                label=suggestion.label,
                profile_kind=suggestion.profile_kind.value,
                groups=[DraftGroupDto.model_validate(group) for group in suggestion.groups],
                group_assignments=[
                    GroupAssignmentDto.model_validate(assignment)
                    for assignment in suggestion.group_assignments
                ],
                seat_assignments=[
                    SeatAssignmentDto.model_validate(assignment)
                    for assignment in suggestion.seat_assignments
                ],
                score_breakdown=suggestion.score_breakdown,
                findings=[
                    ValidationFindingDto.model_validate(finding) for finding in suggestion.findings
                ],
                explanation_bullets=suggestion.explanation_bullets,
                engine_metadata=SuggestionEngineMetadataDto.model_validate(
                    suggestion.engine_metadata
                ),
            )
            for suggestion in result.suggestions
        ]
    )


@router.get("/bootstrap", response_model=ClassroomPlannerBootstrapResponse)
@inject
async def get_bootstrap(
    handler: FromDishka[GetBootstrapHandler],
    user: User = Depends(require_user_api),
) -> ClassroomPlannerBootstrapResponse:
    payload = await handler.handle(owner_user_id=user.id)
    return ClassroomPlannerBootstrapResponse(
        lesson_modes=[LessonModePresetDto.model_validate(mode) for mode in payload.lesson_modes],
        feature_flags=payload.feature_flags,
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
    )
    return _serialize_plan_draft(draft)


@router.get("/drafts/{draft_id}", response_model=PlanDraftDto)
@inject
async def get_draft(
    draft_id: UUID,
    handler: FromDishka[GetDraftHandler],
    user: User = Depends(require_user_api),
) -> PlanDraftDto:
    return _serialize_plan_draft(await handler.handle(draft_id=draft_id, owner_user_id=user.id))


@router.get("/drafts/{draft_id}/workspace", response_model=DraftWorkspaceResponse)
@inject
async def get_draft_workspace(
    draft_id: UUID,
    handler: FromDishka[GetDraftWorkspaceHandler],
    user: User = Depends(require_user_api),
) -> DraftWorkspaceResponse:
    workspace = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return _serialize_workspace(workspace)


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
        lesson_mode_id=request.lesson_mode_id,
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
        pair_constraints=[
            PairConstraint.model_validate(constraint.model_dump())
            for constraint in request.pair_constraints
        ]
        if request.pair_constraints is not None
        else None,
        planning_profile=PlanningProfile.model_validate(request.planning_profile.model_dump())
        if request.planning_profile is not None
        else None,
    )
    return _serialize_plan_draft(draft)


@router.post("/drafts/{draft_id}/validate", response_model=ValidationResultResponse)
@inject
async def validate_draft(
    draft_id: UUID,
    handler: FromDishka[ValidateDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ValidationResultResponse:
    return _serialize_validation(await handler.handle(draft_id=draft_id, owner_user_id=user.id))


@router.post("/drafts/{draft_id}/suggestions", response_model=SuggestionListResponse)
@inject
async def generate_suggestions(
    draft_id: UUID,
    handler: FromDishka[GenerateSuggestionsHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> SuggestionListResponse:
    result = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return _serialize_suggestions(result)


@router.post("/drafts/{draft_id}/suggestions/{suggestion_id}/apply", response_model=PlanDraftDto)
@inject
async def apply_suggestion(
    draft_id: UUID,
    suggestion_id: str,
    request: RevisionRequest,
    handler: FromDishka[ApplySuggestionHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        suggestion_id=suggestion_id,
        expected_revision=request.expected_revision,
    )
    return _serialize_plan_draft(draft)


@router.post("/drafts/{draft_id}/randomize", response_model=PlanDraftDto)
@inject
async def randomize_draft(
    draft_id: UUID,
    request: RevisionRequest,
    handler: FromDishka[RandomizeDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=request.expected_revision,
    )
    return _serialize_plan_draft(draft)


@router.post("/drafts/{draft_id}/finalize", response_model=ArrangementSnapshotDto)
@inject
async def finalize_draft(
    draft_id: UUID,
    handler: FromDishka[FinalizeDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ArrangementSnapshotDto:
    return ArrangementSnapshotDto.model_validate(
        await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    )


@router.get("/snapshots", response_model=list[ArrangementSnapshotDto])
@inject
async def list_snapshots(
    handler: FromDishka[ListSnapshotsHandler],
    user: User = Depends(require_user_api),
) -> list[ArrangementSnapshotDto]:
    return [
        ArrangementSnapshotDto.model_validate(snapshot)
        for snapshot in await handler.handle(owner_user_id=user.id)
    ]


@router.get("/snapshots/{snapshot_id}", response_model=ArrangementSnapshotDto)
@inject
async def get_snapshot(
    snapshot_id: UUID,
    handler: FromDishka[GetSnapshotHandler],
    user: User = Depends(require_user_api),
) -> ArrangementSnapshotDto:
    return ArrangementSnapshotDto.model_validate(
        await handler.handle(snapshot_id=snapshot_id, owner_user_id=user.id)
    )
