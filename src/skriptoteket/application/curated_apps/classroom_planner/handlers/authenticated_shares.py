"""Authenticated Klassrumskartan share creation handlers.

Purpose:
    Coordinate owner-scoped draft loading, strict `expected_revision`
    validation, canonical presentation rendering, and share artifact creation
    for authenticated PR-0274 routes.

Relationships:
    - Reuses grouping/seating export preparation handlers for canonical models.
    - Uses `ClassroomPlannerShareRendererProtocol` for server-side rendering.
    - Persists through `CreateClassroomPlannerShareArtifactHandler`.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.checkpoint_recorders import (
    GroupingCheckpointRecorder,
    SeatingCheckpointRecorder,
    build_grouping_checkpoint,
    build_seating_checkpoint,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.grouping_exports import (
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_exports import (
    PrepareSeatingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.share_artifacts import (
    CreateClassroomPlannerShareArtifactCommand,
    CreateClassroomPlannerShareArtifactHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoint_provenance import (
    CheckpointSourceKind,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareRendererProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class CreateAuthenticatedGroupingShareHandler:
    """Create one immutable authenticated grouping share artifact."""

    def __init__(
        self,
        *,
        prepare_grouping: PrepareGroupingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        checkpoint_recorder: GroupingCheckpointRecorder,
        id_generator: IdGeneratorProtocol,
        renderer: ClassroomPlannerShareRendererProtocol,
    ) -> None:
        self._prepare_grouping = prepare_grouping
        self._create_artifact = create_artifact
        self._checkpoint_recorder = checkpoint_recorder
        self._id_generator = id_generator
        self._renderer = renderer

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
    ) -> ClassroomPlannerShareArtifactCreateResult:
        workspace = await self._prepare_grouping.load_workspace(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        _validate_expected_revision(
            actual_revision=workspace.draft.revision,
            expected_revision=expected_revision,
        )
        prepared_export = self._prepare_grouping.build_prepared_contract(
            workspace=workspace,
            export_kind=GroupingExportKind.PDF,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        )
        rendered = self._renderer.render_grouping(prepared_export=prepared_export)

        async def record_checkpoint(artifact: ClassroomPlannerShareArtifact) -> None:
            await self._checkpoint_recorder.record(
                checkpoint=build_grouping_checkpoint(
                    workspace=workspace,
                    checkpoint_id=self._id_generator.new_uuid(),
                    created_at=artifact.created_at,
                    source_kind=CheckpointSourceKind.SHARE_ARTIFACT,
                    source_share_artifact_id=artifact.id,
                )
            )

        return await self._create_artifact.handle(
            command=CreateClassroomPlannerShareArtifactCommand(
                source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
                draft_kind=PlanDraftKind.GROUPING,
                owner_user_id=owner_user_id,
                draft_id=draft_id,
                roster_id=workspace.roster.id,
                template_id=workspace.draft.template_id,
                source_revision=workspace.draft.revision,
                title=rendered.title,
                preview_description=rendered.preview_description,
                renderer_version=rendered.renderer_version,
                presentation_schema_version=rendered.presentation_schema_version,
                presentation_payload=rendered.presentation_payload,
                rendered_html=rendered.rendered_html,
                rendered_css=rendered.rendered_css,
            ),
            after_persist=record_checkpoint,
        )


class CreateAuthenticatedSeatingShareHandler:
    """Create one immutable authenticated seating share artifact."""

    def __init__(
        self,
        *,
        prepare_seating: PrepareSeatingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        checkpoint_recorder: SeatingCheckpointRecorder,
        id_generator: IdGeneratorProtocol,
        renderer: ClassroomPlannerShareRendererProtocol,
    ) -> None:
        self._prepare_seating = prepare_seating
        self._create_artifact = create_artifact
        self._checkpoint_recorder = checkpoint_recorder
        self._id_generator = id_generator
        self._renderer = renderer

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
    ) -> ClassroomPlannerShareArtifactCreateResult:
        workspace = await self._prepare_seating.load_workspace(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        _validate_expected_revision(
            actual_revision=workspace.draft.revision,
            expected_revision=expected_revision,
        )
        prepared_export = self._prepare_seating.build_prepared_contract(
            workspace=workspace,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )
        rendered = self._renderer.render_seating(prepared_export=prepared_export)

        async def record_checkpoint(artifact: ClassroomPlannerShareArtifact) -> None:
            await self._checkpoint_recorder.record(
                checkpoint=build_seating_checkpoint(
                    workspace=workspace,
                    checkpoint_id=self._id_generator.new_uuid(),
                    created_at=artifact.created_at,
                    source_kind=CheckpointSourceKind.SHARE_ARTIFACT,
                    source_share_artifact_id=artifact.id,
                )
            )

        return await self._create_artifact.handle(
            command=CreateClassroomPlannerShareArtifactCommand(
                source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
                draft_kind=PlanDraftKind.SEATING,
                owner_user_id=owner_user_id,
                draft_id=draft_id,
                roster_id=workspace.roster.id,
                template_id=workspace.draft.template_id,
                source_revision=workspace.draft.revision,
                title=rendered.title,
                preview_description=rendered.preview_description,
                renderer_version=rendered.renderer_version,
                presentation_schema_version=rendered.presentation_schema_version,
                presentation_payload=rendered.presentation_payload,
                rendered_html=rendered.rendered_html,
                rendered_css=rendered.rendered_css,
            ),
            after_persist=record_checkpoint,
        )


def _validate_expected_revision(*, actual_revision: int, expected_revision: int) -> None:
    if actual_revision == expected_revision:
        return
    raise DomainError(
        code=ErrorCode.CONFLICT,
        message=f"Draft revision mismatch. Expected {expected_revision}, got {actual_revision}.",
        details={
            "expected_revision": expected_revision,
            "actual_revision": actual_revision,
        },
    )
