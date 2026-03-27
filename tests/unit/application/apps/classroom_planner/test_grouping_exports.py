"""Behavior tests for classroom-planner grouping export preparation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    GroupingExportKind,
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    build_grouping_export_presentation,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)


@pytest.fixture
def drafts():
    return AsyncMock(spec=PlanDraftRepositoryProtocol)


@pytest.fixture
def rosters():
    return AsyncMock(spec=RosterRepositoryProtocol)


@pytest.fixture
def templates():
    return AsyncMock(spec=RoomTemplateRepositoryProtocol)


def _build_active_grouping_draft(*, owner_user_id, roster_id, template_id=None) -> PlanDraft:
    now = datetime.now(timezone.utc)
    return PlanDraft(
        id=uuid4(),
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _build_roster(*, owner_user_id, roster_id) -> Roster:
    now = datetime.now(timezone.utc)
    return Roster(
        id=roster_id,
        owner_user_id=owner_user_id,
        name="Klass 7A",
        students=[
            Student(id="student-2", display_name="Bo Berg"),
            Student(id="student-1", display_name="Ada Lovelace"),
            Student(id="student-3", display_name="Linus Torvalds"),
        ],
        created_at=now,
        updated_at=now,
    )


def _build_template(*, owner_user_id, template_id) -> RoomTemplate:
    now = datetime.now(timezone.utc)
    return RoomTemplate(
        id=template_id,
        owner_user_id=owner_user_id,
        name="Sal A",
        grid_cols=10,
        grid_rows=8,
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_grouping_export_returns_ordered_presentation(drafts, rosters, templates):
    owner_user_id = uuid4()
    roster_id = uuid4()
    draft = _build_active_grouping_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=draft,
        groups=[
            DraftGroup(id="group-2", name="Grupp 2", sort_order=1),
            DraftGroup(id="group-1", name="Grupp 1", sort_order=0),
        ],
        group_assignments=[
            GroupAssignment(student_id="student-1", group_id="group-2"),
            GroupAssignment(student_id="student-2", group_id="group-1"),
        ],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )
    rosters.get_by_id.return_value = _build_roster(owner_user_id=owner_user_id, roster_id=roster_id)
    handler = PrepareGroupingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    result = await handler.handle(
        draft_id=draft.id,
        owner_user_id=owner_user_id,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
    )

    assert result.grouping_draft_id == draft.id
    assert result.export_kind is GroupingExportKind.XLSX
    assert [group.group_label for group in result.presentation.groups] == ["Grupp 1", "Grupp 2"]
    assert [member.display_name for member in result.presentation.groups[0].members] == ["Bo Berg"]
    assert [member.display_name for member in result.presentation.groups[1].members] == [
        "Ada Lovelace"
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_grouping_export_hydrates_template_from_draft_context(
    drafts,
    rosters,
    templates,
):
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft = _build_active_grouping_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    drafts.get_workspace.return_value = DraftWorkspace(draft=draft)
    rosters.get_by_id.return_value = _build_roster(owner_user_id=owner_user_id, roster_id=roster_id)
    templates.get_by_id.return_value = _build_template(
        owner_user_id=owner_user_id,
        template_id=template_id,
    )
    handler = PrepareGroupingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    result = await handler.handle(
        draft_id=draft.id,
        owner_user_id=owner_user_id,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
    )

    assert result.grouping_draft_id == draft.id
    templates.get_by_id.assert_awaited_once_with(template_id=template_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_grouping_export_rejects_pdf_without_paper_size(drafts, rosters, templates):
    owner_user_id = uuid4()
    roster_id = uuid4()
    draft = _build_active_grouping_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=draft,
    )
    rosters.get_by_id.return_value = _build_roster(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    handler = PrepareGroupingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            draft_id=draft.id,
            owner_user_id=owner_user_id,
            export_kind=GroupingExportKind.PDF,
            paper_size=None,
        )

    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_build_grouping_export_presentation_rejects_duplicate_assignments():
    now = datetime.now(timezone.utc)
    owner_user_id = uuid4()
    roster_id = uuid4()
    workspace = ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            status=PlanDraftStatus.ACTIVE,
            revision=2,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[Student(id="student-1", display_name="Ada Lovelace")],
            created_at=now,
            updated_at=now,
        ),
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0)],
        group_assignments=[
            GroupAssignment(student_id="student-1", group_id="group-1"),
            GroupAssignment(student_id="student-1", group_id="group-1"),
        ],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )

    with pytest.raises(DomainError) as error:
        build_grouping_export_presentation(workspace=workspace)

    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_grouping_export_rejects_non_grouping_draft(drafts, rosters, templates):
    owner_user_id = uuid4()
    roster_id = uuid4()
    draft = _build_active_grouping_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    ).model_copy(update={"draft_kind": PlanDraftKind.SEATING})
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=draft,
    )
    rosters.get_by_id.return_value = _build_roster(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    handler = PrepareGroupingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            draft_id=draft.id,
            owner_user_id=owner_user_id,
            export_kind=GroupingExportKind.XLSX,
            paper_size=None,
        )

    assert error.value.code == ErrorCode.VALIDATION_ERROR
