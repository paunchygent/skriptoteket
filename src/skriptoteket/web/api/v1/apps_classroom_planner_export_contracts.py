"""Web DTOs for Klassrumskartan export preparation contracts.

Purpose:
    Define the public request and response contracts for seating and grouping
    export preparation so the classroom-planner API can expose typed artifact
    seams without leaking application internals directly.

Relationships:
    - Serializes application export models from
      `skriptoteket.application.curated_apps.classroom_planner.exports`.
    - Used by the seating-specific classroom-planner API router.
    - Locks the PR-0118 contract shape ahead of PR-0119 rendering work.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    PosterSceneFixtureKind,
    PosterSceneFixtureVariant,
    PosterSceneWallSide,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)


class PrepareSeatingExportRequest(BaseModel):
    """Deserialize a typed seating export-preparation request."""

    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId


class PosterSceneRoomDto(BaseModel):
    """Serialize the logical room grid for the poster scene."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    grid_cols: int
    grid_rows: int


class PosterSceneSeatDto(BaseModel):
    """Serialize one logical poster seat placement."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    seat_id: str
    x: int
    y: int
    zone: str | None = None
    student_id: str | None = None
    label: str | None = None


class PosterSceneFixtureDto(BaseModel):
    """Serialize one logical poster room marker."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    fixture_id: str
    kind: PosterSceneFixtureKind
    x: int
    y: int
    width: int
    height: int
    wall_side: PosterSceneWallSide | None = None
    label: str | None = None
    variant: PosterSceneFixtureVariant | None = None


class SeatingPosterSceneDto(BaseModel):
    """Serialize the standalone poster scene prepared for export."""

    model_config = ConfigDict(frozen=True)

    room: PosterSceneRoomDto
    seats: list[PosterSceneSeatDto]
    fixtures: list[PosterSceneFixtureDto]


class PreparedSeatingExportDto(BaseModel):
    """Serialize the public seating export contract."""

    model_config = ConfigDict(frozen=True)

    seating_draft_id: UUID
    roster_id: UUID
    roster_name: str
    template_id: UUID
    template_name: str
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId
    poster_scene: SeatingPosterSceneDto


class PrepareGroupingExportRequest(BaseModel):
    """Deserialize a typed grouping export-preparation request."""

    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None


class GroupingPresentationMemberDto(BaseModel):
    """Serialize one ordered member inside a grouping export contract."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    member_order: int
    display_name: str


class GroupingPresentationGroupDto(BaseModel):
    """Serialize one teacher-facing group inside the shared presentation contract."""

    model_config = ConfigDict(frozen=True)

    group_label: str
    group_order: int
    members: list[GroupingPresentationMemberDto]


class GroupingExportPresentationDto(BaseModel):
    """Serialize the shared grouping presentation prepared for export."""

    model_config = ConfigDict(frozen=True)

    class_name: str
    title: str
    groups: list[GroupingPresentationGroupDto]
    filename_stem: str


class PreparedGroupingExportDto(BaseModel):
    """Serialize the public grouping export contract."""

    model_config = ConfigDict(frozen=True)

    draft_id: UUID
    draft_kind: str
    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None
    presentation: GroupingExportPresentationDto


def serialize_prepared_seating_export(
    prepared_export: PreparedSeatingExportContract,
) -> PreparedSeatingExportDto:
    """Map an application seating export contract to the public API DTO."""

    return PreparedSeatingExportDto(
        seating_draft_id=prepared_export.seating_draft_id,
        roster_id=prepared_export.roster_id,
        roster_name=prepared_export.roster_name,
        template_id=prepared_export.template_id,
        template_name=prepared_export.template_name,
        export_kind=prepared_export.export_kind,
        layout_id=prepared_export.layout_id,
        poster_scene=_serialize_poster_scene(prepared_export.poster_scene),
    )


def serialize_prepared_grouping_export(
    prepared_export: PreparedGroupingExportContract,
) -> PreparedGroupingExportDto:
    """Map an application grouping export contract to the public API DTO."""

    return PreparedGroupingExportDto(
        draft_id=prepared_export.grouping_draft_id,
        draft_kind="grouping",
        export_kind=prepared_export.export_kind,
        paper_size=prepared_export.paper_size,
        presentation=_serialize_grouping_presentation(prepared_export.presentation),
    )


def _serialize_poster_scene(scene: SeatingPosterScene) -> SeatingPosterSceneDto:
    """Serialize the prepared poster scene payload."""

    return SeatingPosterSceneDto(
        room=PosterSceneRoomDto.model_validate(scene.room),
        seats=[PosterSceneSeatDto.model_validate(seat) for seat in scene.seats],
        fixtures=[PosterSceneFixtureDto.model_validate(fixture) for fixture in scene.fixtures],
    )


def _serialize_grouping_presentation(
    presentation: GroupingExportPresentation,
) -> GroupingExportPresentationDto:
    """Serialize the shared grouping presentation payload."""

    return GroupingExportPresentationDto(
        class_name=presentation.class_name,
        title=presentation.title,
        groups=[
            GroupingPresentationGroupDto(
                group_label=group.group_label,
                group_order=group.group_order,
                members=[
                    GroupingPresentationMemberDto.model_validate(member) for member in group.members
                ],
            )
            for group in presentation.groups
        ],
        filename_stem=presentation.filename_stem,
    )
