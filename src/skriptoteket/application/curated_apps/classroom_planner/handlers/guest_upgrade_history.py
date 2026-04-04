"""Historical import collaborators for Klassrumskartan guest upgrades.

This module owns the idempotent import of historical drafts and export-backed
checkpoints so the main guest-upgrade handler can coordinate the flow without
embedding every persistence decision in one class.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports.grouping_jobs import (
    GroupingExportJob,
    GroupingExportJobStatus,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.grouping_presentation import (
    GroupingExportKind,
    GroupingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportJob,
    SeatingExportJobStatus,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.models import (
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeReceiptItem,
    ClassroomPlannerGuestUpgradeRequest,
    GuestUpgradeCheckpointPayload,
    GuestUpgradeDraftPayload,
    build_guest_import_identity,
    build_server_draft_fingerprint,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
    build_assignment_hash,
    build_normalized_seating_snapshot,
    build_room_context_hash,
    build_room_context_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    build_grouping_assignment_hash,
    build_normalized_grouping_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    SeatAssignment,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    SeatingExportJobRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_guest_upgrade import (
    ClassroomPlannerGuestUpgradeRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol

from .guest_upgrade_support import (
    MappedRoster,
    MappedTemplate,
    build_preview_uuid,
    parse_guest_datetime,
)
from .workspace_validation import ensure_valid_workspace_structure


class GuestUpgradeHistoryImporter:
    """Import historical drafts and checkpoints for one guest-upgrade request."""

    def __init__(
        self,
        *,
        drafts: PlanDraftRepositoryProtocol,
        seating_checkpoints: SeatingExportCheckpointRepositoryProtocol,
        grouping_checkpoints: GroupingExportCheckpointRepositoryProtocol,
        seating_export_jobs: SeatingExportJobRepositoryProtocol,
        grouping_export_jobs: GroupingExportJobRepositoryProtocol,
        guest_upgrade_repository: ClassroomPlannerGuestUpgradeRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._drafts = drafts
        self._seating_checkpoints = seating_checkpoints
        self._grouping_checkpoints = grouping_checkpoints
        self._seating_export_jobs = seating_export_jobs
        self._grouping_export_jobs = grouping_export_jobs
        self._guest_upgrade_repository = guest_upgrade_repository
        self._clock = clock
        self._id_generator = id_generator

    async def import_drafts(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        roster_cache: dict[str, MappedRoster],
        template_cache: dict[str, MappedTemplate],
    ) -> dict[PlanDraftKind, PlanDraft]:
        """Import or reuse the snapshot's historical grouping and seating drafts."""

        imported_drafts: dict[PlanDraftKind, PlanDraft] = {}
        for draft_payload in [snapshot.grouping_draft, snapshot.seating_draft]:
            if draft_payload is None:
                continue
            draft = await self._import_draft(
                owner_user_id=owner_user_id,
                request=request,
                snapshot=snapshot,
                receipt=receipt,
                roster_cache=roster_cache,
                template_cache=template_cache,
                draft_payload=draft_payload,
            )
            if draft is not None:
                imported_drafts[draft_payload.draft_kind] = draft
        return imported_drafts

    async def import_checkpoints(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        roster_cache: dict[str, MappedRoster],
        template_cache: dict[str, MappedTemplate],
        imported_drafts: dict[PlanDraftKind, PlanDraft],
    ) -> None:
        """Import or reuse the snapshot's export-backed checkpoints."""

        for checkpoint in snapshot.checkpoint_descriptors:
            await self._import_checkpoint(
                owner_user_id=owner_user_id,
                request=request,
                snapshot=snapshot,
                receipt=receipt,
                roster_cache=roster_cache,
                template_cache=template_cache,
                imported_drafts=imported_drafts,
                checkpoint=checkpoint,
            )

    async def _import_draft(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        roster_cache: dict[str, MappedRoster],
        template_cache: dict[str, MappedTemplate],
        draft_payload: GuestUpgradeDraftPayload,
    ) -> PlanDraft | None:
        mapped_roster = roster_cache.get(draft_payload.roster_local_id)
        if mapped_roster is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message="Draft references an unmapped roster.",
                )
            )
            return None

        mapped_template = (
            template_cache.get(draft_payload.template_local_id)
            if draft_payload.template_local_id is not None
            else None
        )
        if draft_payload.template_local_id is not None and mapped_template is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message="Draft references an unmapped room template.",
                )
            )
            return None

        import_identity = build_guest_import_identity(
            snapshot_id=snapshot.snapshot_id,
            server_snapshot_content_hash=snapshot.snapshot_content_hash,
            draft_payload=draft_payload.model_copy(
                update={"fingerprint": build_server_draft_fingerprint(draft_payload)}
            ),
        )
        existing = await self._guest_upgrade_repository.get_imported_draft_by_identity(
            owner_user_id=owner_user_id,
            guest_import_identity=import_identity,
        )
        if existing is not None:
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    target_id=str(existing.id),
                )
            )
            return existing

        now = self._clock.now()
        if draft_payload.group_assignments and any(
            assignment.student_id not in mapped_roster.student_id_map
            for assignment in draft_payload.group_assignments
        ):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message="Draft group assignments reference unmapped roster students.",
                )
            )
            return None
        if draft_payload.seat_assignments and mapped_template is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message="Draft seat assignments require an imported room template.",
                )
            )
            return None
        if draft_payload.seat_assignments and any(
            assignment.student_id not in mapped_roster.student_id_map
            or assignment.seat_id not in mapped_template.seat_id_map
            for assignment in draft_payload.seat_assignments
            if mapped_template is not None
        ):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message="Draft seat assignments reference unmapped students or seats.",
                )
            )
            return None
        draft = PlanDraft(
            id=(
                self._id_generator.new_uuid()
                if request.mode == "commit"
                else build_preview_uuid(
                    snapshot_id=snapshot.snapshot_id,
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                )
            ),
            owner_user_id=owner_user_id,
            roster_id=mapped_roster.roster.id,
            draft_kind=draft_payload.draft_kind,
            template_id=mapped_template.template.id if mapped_template else None,
            task_entry_classroom_selection_mode=draft_payload.task_entry_classroom_selection_mode,
            smart_enabled=draft_payload.smart_enabled,
            use_history=draft_payload.use_history,
            grouping_seating_distance_enabled=draft_payload.grouping_seating_distance_enabled,
            status=PlanDraftStatus.SUPERSEDED,
            guest_import_identity=import_identity,
            revision=draft_payload.revision,
            last_opened_at=parse_guest_datetime(draft_payload.last_opened_at, fallback=now),
            created_at=now,
            updated_at=now,
        )
        workspace = DraftWorkspace(
            draft=draft,
            groups=[
                DraftGroup(
                    id=group.id,
                    name=group.name,
                    sort_order=group.sort_order,
                    name_is_custom=group.name_is_custom,
                )
                for group in draft_payload.groups
            ],
            group_assignments=[
                GroupAssignment(
                    student_id=mapped_roster.student_id_map[assignment.student_id],
                    group_id=assignment.group_id,
                )
                for assignment in draft_payload.group_assignments
            ],
            seat_assignments=[
                SeatAssignment(
                    student_id=mapped_roster.student_id_map[assignment.student_id],
                    seat_id=mapped_template.seat_id_map[assignment.seat_id],
                )
                for assignment in draft_payload.seat_assignments
                if mapped_template is not None
            ],
        )
        try:
            ensure_valid_workspace_structure(
                workspace=workspace,
                roster=mapped_roster.roster,
                template=mapped_template.template if mapped_template is not None else None,
            )
        except DomainError as error:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="draft",
                    local_id=draft_payload.local_id,
                    draft_kind=draft_payload.draft_kind,
                    message=error.message,
                )
            )
            return None
        if request.mode == "commit":
            await self._drafts.save_workspace(workspace=workspace)
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="draft",
                local_id=draft_payload.local_id,
                draft_kind=draft_payload.draft_kind,
                target_id=str(draft.id) if request.mode == "commit" else None,
            )
        )
        return draft

    async def _import_checkpoint(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        roster_cache: dict[str, MappedRoster],
        template_cache: dict[str, MappedTemplate],
        imported_drafts: dict[PlanDraftKind, PlanDraft],
        checkpoint: GuestUpgradeCheckpointPayload,
    ) -> None:
        draft = imported_drafts.get(checkpoint.draft_kind)
        related_payload = (
            snapshot.grouping_draft
            if checkpoint.draft_kind is PlanDraftKind.GROUPING
            else snapshot.seating_draft
        )
        if draft is None or related_payload is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message=(
                        "Checkpoint import requires a corresponding imported draft in this slice."
                    ),
                )
            )
            return

        mapped_roster = roster_cache.get(related_payload.roster_local_id)
        if mapped_roster is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message="Checkpoint references an unmapped roster.",
                )
            )
            return

        if checkpoint.draft_kind is PlanDraftKind.GROUPING:
            await self._import_grouping_checkpoint(
                owner_user_id=owner_user_id,
                request=request,
                receipt=receipt,
                checkpoint=checkpoint,
                draft=draft,
                mapped_roster=mapped_roster,
            )
            return

        mapped_template = (
            template_cache.get(checkpoint.template_local_id)
            if checkpoint.template_local_id is not None
            else None
        )
        if mapped_template is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message="Seating checkpoint requires an imported or reused room template.",
                )
            )
            return
        await self._import_seating_checkpoint(
            owner_user_id=owner_user_id,
            request=request,
            receipt=receipt,
            checkpoint=checkpoint,
            draft=draft,
            mapped_roster=mapped_roster,
            mapped_template=mapped_template,
        )

    async def _import_grouping_checkpoint(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        checkpoint: GuestUpgradeCheckpointPayload,
        draft: PlanDraft,
        mapped_roster: MappedRoster,
    ) -> None:
        if checkpoint.group_assignments is None:
            raise ValueError("Grouping checkpoints must include group_assignments.")
        if any(
            assignment.student_id not in mapped_roster.student_id_map
            for assignment in checkpoint.group_assignments
        ):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message="Grouping checkpoint references unmapped roster students.",
                )
            )
            return
        grouping_assignments = [
            GroupAssignment(
                student_id=mapped_roster.student_id_map[assignment.student_id],
                group_id=assignment.group_id,
            )
            for assignment in checkpoint.group_assignments
        ]
        grouping_snapshot = build_normalized_grouping_snapshot(
            roster=mapped_roster.roster,
            group_assignments=grouping_assignments,
        )
        checkpoint_student_ids = [
            mapped_roster.student_id_map[assignment.student_id]
            for assignment in checkpoint.group_assignments
        ]
        if len(checkpoint_student_ids) != len(set(checkpoint_student_ids)):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message="Grouping checkpoint assigns the same student more than once.",
                )
            )
            return
        assignment_hash = build_grouping_assignment_hash(grouping_snapshot=grouping_snapshot)
        exists = await self._guest_upgrade_repository.grouping_checkpoint_exists(
            roster_id=mapped_roster.roster.id,
            assignment_hash=assignment_hash,
        )
        if exists:
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                )
            )
            return
        if request.mode == "commit":
            now = self._clock.now()
            export_job = GroupingExportJob(
                id=self._id_generator.new_uuid(),
                owner_user_id=owner_user_id,
                draft_id=draft.id,
                roster_id=mapped_roster.roster.id,
                export_kind=GroupingExportKind.PDF,
                paper_size=GroupingExportPaperSize.A4_PORTRAIT,
                output_filename=f"guest-import-{checkpoint.local_id}-grouping.pdf",
                status=GroupingExportJobStatus.SUCCEEDED,
                created_at=now,
                updated_at=now,
            )
            await self._grouping_export_jobs.create(job=export_job)
            await self._grouping_checkpoints.create(
                checkpoint=GroupingExportCheckpoint(
                    id=self._id_generator.new_uuid(),
                    roster_id=mapped_roster.roster.id,
                    template_id=draft.template_id,
                    source_draft_id=draft.id,
                    source_export_job_id=export_job.id,
                    assignment_hash=assignment_hash,
                    grouping_snapshot=grouping_snapshot,
                    created_at=parse_guest_datetime(checkpoint.created_at, fallback=now),
                )
            )
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="checkpoint",
                local_id=checkpoint.local_id,
                draft_kind=checkpoint.draft_kind,
            )
        )

    async def _import_seating_checkpoint(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        checkpoint: GuestUpgradeCheckpointPayload,
        draft: PlanDraft,
        mapped_roster: MappedRoster,
        mapped_template: MappedTemplate,
    ) -> None:
        if checkpoint.template_local_id is None:
            raise ValueError("Seating checkpoints must include template_local_id.")
        if checkpoint.seat_assignments is None:
            raise ValueError("Seating checkpoints must include seat_assignments.")
        if any(
            assignment.student_id not in mapped_roster.student_id_map
            or assignment.seat_id not in mapped_template.seat_id_map
            for assignment in checkpoint.seat_assignments
        ):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message="Seating checkpoint references unmapped students or room seats.",
                )
            )
            return
        seating_assignments = [
            SeatAssignment(
                student_id=mapped_roster.student_id_map[assignment.student_id],
                seat_id=mapped_template.seat_id_map[assignment.seat_id],
            )
            for assignment in checkpoint.seat_assignments
        ]
        workspace = ClassroomPlannerWorkspace(
            draft=draft,
            roster=mapped_roster.roster,
            template=mapped_template.template,
            seat_assignments=seating_assignments,
        )
        try:
            ensure_valid_workspace_structure(
                workspace=DraftWorkspace(
                    draft=draft,
                    groups=[],
                    group_assignments=[],
                    seat_assignments=workspace.seat_assignments,
                ),
                roster=mapped_roster.roster,
                template=mapped_template.template,
            )
        except DomainError as error:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                    message=error.message,
                )
            )
            return
        room_context = build_room_context_snapshot(workspace=workspace)
        seating_snapshot = build_normalized_seating_snapshot(workspace=workspace)
        room_context_hash = build_room_context_hash(room_context=room_context)
        assignment_hash = build_assignment_hash(seating_snapshot=seating_snapshot)
        exists = await self._guest_upgrade_repository.seating_checkpoint_exists(
            roster_id=mapped_roster.roster.id,
            room_context_hash=room_context_hash,
            assignment_hash=assignment_hash,
        )
        if exists:
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="checkpoint",
                    local_id=checkpoint.local_id,
                    draft_kind=checkpoint.draft_kind,
                )
            )
            return
        if request.mode == "commit":
            now = self._clock.now()
            export_job = SeatingExportJob(
                id=self._id_generator.new_uuid(),
                owner_user_id=owner_user_id,
                draft_id=draft.id,
                roster_id=mapped_roster.roster.id,
                template_id=mapped_template.template.id,
                export_kind=SeatingExportKind.PDF,
                layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
                paper_size=SeatingExportPaperSize.A4_LANDSCAPE,
                output_filename=f"guest-import-{checkpoint.local_id}-seating.pdf",
                status=SeatingExportJobStatus.SUCCEEDED,
                created_at=now,
                updated_at=now,
            )
            await self._seating_export_jobs.create(job=export_job)
            await self._seating_checkpoints.create(
                checkpoint=SeatingExportCheckpoint(
                    id=self._id_generator.new_uuid(),
                    roster_id=mapped_roster.roster.id,
                    template_id=mapped_template.template.id,
                    source_draft_id=draft.id,
                    source_export_job_id=export_job.id,
                    room_context_hash=room_context_hash,
                    assignment_hash=assignment_hash,
                    room_context=room_context,
                    seating_snapshot=seating_snapshot,
                    created_at=parse_guest_datetime(checkpoint.created_at, fallback=now),
                )
            )
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="checkpoint",
                local_id=checkpoint.local_id,
                draft_kind=checkpoint.draft_kind,
            )
        )
