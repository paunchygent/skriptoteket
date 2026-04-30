"""Behavior tests for authenticated Klassrumskartan share creation.

Purpose:
    Lock the PR-0274 authenticated share route foundation: handlers must
    enforce the typed `expected_revision` before rendering and persist only
    canonical backend-rendered share artifacts.

Relationships:
    - Exercises `CreateAuthenticatedGroupingShareHandler` and
      `CreateAuthenticatedSeatingShareHandler`.
    - Uses protocol-style mocks around export preparation, rendering, and
      share artifact creation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
    CreateAuthenticatedGroupingShareHandler,
    CreateAuthenticatedSeatingShareHandler,
    CreateClassroomPlannerShareArtifactHandler,
    PrepareGroupingExportHandler,
    PrepareSeatingExportHandler,
    RenderedClassroomPlannerShare,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    GroupingPresentationGroup,
    PosterSceneRoom,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareRendererProtocol,
)


def _workspace(*, draft_kind: PlanDraftKind, revision: int) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=draft_kind,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=revision,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal A",
            seats=[],
            fixtures=[],
            created_at=now,
            updated_at=now,
        ),
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _grouping_contract(workspace: ClassroomPlannerWorkspace) -> PreparedGroupingExportContract:
    return PreparedGroupingExportContract(
        grouping_draft_id=workspace.draft.id,
        roster_id=workspace.roster.id,
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        presentation=GroupingExportPresentation(
            draft_id=workspace.draft.id,
            class_name=workspace.roster.name,
            title="Gruppindelning",
            filename_stem="klass-7a-gruppindelning",
            groups=(GroupingPresentationGroup(group_label="Grupp 1", group_order=0, members=()),),
        ),
    )


def _seating_contract(workspace: ClassroomPlannerWorkspace) -> PreparedSeatingExportContract:
    assert workspace.template is not None
    return PreparedSeatingExportContract(
        seating_draft_id=workspace.draft.id,
        roster_id=workspace.roster.id,
        roster_name=workspace.roster.name,
        template_id=workspace.template.id,
        template_name=workspace.template.name,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[],
            fixtures=[],
        ),
    )


def _rendered() -> RenderedClassroomPlannerShare:
    return RenderedClassroomPlannerShare(
        title="Klass 7A",
        preview_description="Frozen plan",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_payload={"title": "Klass 7A"},
        rendered_html="<html>Klass 7A</html>",
        rendered_css="body { color: black; }",
    )


def _result(*, source_revision: int) -> ClassroomPlannerShareArtifactCreateResult:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    return ClassroomPlannerShareArtifactCreateResult(
        public_token="public-token",
        artifact=ClassroomPlannerShareArtifact(
            id=uuid4(),
            token_hash="sha256:stored",
            source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
            draft_kind=PlanDraftKind.GROUPING,
            owner_user_id=uuid4(),
            draft_id=uuid4(),
            roster_id=uuid4(),
            source_revision=source_revision,
            title="Klass 7A",
            slug="klass-7a",
            renderer_version="klassrumskartan-share-renderer-v1",
            presentation_schema_version="grouping-share-v1",
            presentation_hash="sha256:presentation",
            content_hash="sha256:content",
            presentation_payload={"title": "Klass 7A"},
            rendered_html="<html>Klass 7A</html>",
            rendered_css="body { color: black; }",
            created_at=now,
            updated_at=now,
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_share_enforces_expected_revision_before_persisting() -> None:
    workspace = _workspace(draft_kind=PlanDraftKind.GROUPING, revision=7)
    prepare = AsyncMock(spec=PrepareGroupingExportHandler)
    prepare.load_workspace.return_value = workspace
    renderer = MagicMock(spec=ClassroomPlannerShareRendererProtocol)
    create_artifact = AsyncMock(spec=CreateClassroomPlannerShareArtifactHandler)
    handler = CreateAuthenticatedGroupingShareHandler(
        prepare_grouping=prepare,
        create_artifact=create_artifact,
        renderer=renderer,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            draft_id=workspace.draft.id,
            owner_user_id=workspace.draft.owner_user_id,
            expected_revision=6,
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.details == {"expected_revision": 6, "actual_revision": 7}
    prepare.build_prepared_contract.assert_not_called()
    renderer.render_grouping.assert_not_called()
    create_artifact.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_share_uses_canonical_renderer_output() -> None:
    workspace = _workspace(draft_kind=PlanDraftKind.GROUPING, revision=7)
    prepared = _grouping_contract(workspace)
    rendered = _rendered()
    prepare = AsyncMock(spec=PrepareGroupingExportHandler)
    prepare.load_workspace.return_value = workspace
    prepare.build_prepared_contract.return_value = prepared
    renderer = MagicMock(spec=ClassroomPlannerShareRendererProtocol)
    renderer.render_grouping.return_value = rendered
    create_artifact = AsyncMock(spec=CreateClassroomPlannerShareArtifactHandler)
    create_artifact.handle.return_value = _result(source_revision=workspace.draft.revision)
    handler = CreateAuthenticatedGroupingShareHandler(
        prepare_grouping=prepare,
        create_artifact=create_artifact,
        renderer=renderer,
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=workspace.draft.owner_user_id,
        expected_revision=7,
    )

    prepare.build_prepared_contract.assert_called_once_with(
        workspace=workspace,
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
    )
    renderer.render_grouping.assert_called_once_with(prepared_export=prepared)
    command = create_artifact.handle.await_args.kwargs["command"]
    assert command.source is ClassroomPlannerShareArtifactSource.AUTHENTICATED
    assert command.draft_kind is PlanDraftKind.GROUPING
    assert command.owner_user_id == workspace.draft.owner_user_id
    assert command.draft_id == workspace.draft.id
    assert command.roster_id == workspace.roster.id
    assert command.template_id == workspace.draft.template_id
    assert command.source_revision == 7
    assert command.renderer_version == rendered.renderer_version
    assert command.presentation_schema_version == rendered.presentation_schema_version
    assert command.presentation_payload == rendered.presentation_payload
    assert command.rendered_html == rendered.rendered_html
    assert command.rendered_css == rendered.rendered_css
    assert result.public_token == "public-token"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_share_enforces_expected_revision_before_persisting() -> None:
    workspace = _workspace(draft_kind=PlanDraftKind.SEATING, revision=4)
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    prepare.load_workspace.return_value = workspace
    renderer = MagicMock(spec=ClassroomPlannerShareRendererProtocol)
    create_artifact = AsyncMock(spec=CreateClassroomPlannerShareArtifactHandler)
    handler = CreateAuthenticatedSeatingShareHandler(
        prepare_seating=prepare,
        create_artifact=create_artifact,
        renderer=renderer,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            draft_id=workspace.draft.id,
            owner_user_id=workspace.draft.owner_user_id,
            expected_revision=3,
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    prepare.build_prepared_contract.assert_not_called()
    renderer.render_seating.assert_not_called()
    create_artifact.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_share_uses_pretty_brutalist_poster_contract() -> None:
    workspace = _workspace(draft_kind=PlanDraftKind.SEATING, revision=4)
    prepared = _seating_contract(workspace)
    rendered = _rendered().model_copy(update={"presentation_schema_version": "seating-share-v1"})
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    prepare.load_workspace.return_value = workspace
    prepare.build_prepared_contract.return_value = prepared
    renderer = MagicMock(spec=ClassroomPlannerShareRendererProtocol)
    renderer.render_seating.return_value = rendered
    create_artifact = AsyncMock(spec=CreateClassroomPlannerShareArtifactHandler)
    create_artifact.handle.return_value = _result(source_revision=workspace.draft.revision)
    handler = CreateAuthenticatedSeatingShareHandler(
        prepare_seating=prepare,
        create_artifact=create_artifact,
        renderer=renderer,
    )

    await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=workspace.draft.owner_user_id,
        expected_revision=4,
    )

    prepare.build_prepared_contract.assert_called_once_with(
        workspace=workspace,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
    )
    renderer.render_seating.assert_called_once_with(prepared_export=prepared)
    command = create_artifact.handle.await_args.kwargs["command"]
    assert command.draft_kind is PlanDraftKind.SEATING
    assert command.template_id == workspace.draft.template_id
    assert command.source_revision == 4
    assert command.presentation_schema_version == "seating-share-v1"
