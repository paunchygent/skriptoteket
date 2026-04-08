"""Authenticated guest-upgrade orchestration for Klassrumskartan.

This handler coordinates the authenticated guest-upgrade boundary by delegating
asset resolution and historical import work to focused collaborators, keeping
the entrypoint small, explicit, and free of monolithic persistence logic.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
    recompute_server_snapshot,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
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
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .guest_upgrade_assets import GuestUpgradeAssetImporter
from .guest_upgrade_consumption import APP_ID
from .guest_upgrade_history import GuestUpgradeHistoryImporter


def _receipt_consumed_meaningfully(receipt: ClassroomPlannerGuestUpgradeReceipt) -> bool:
    return len(receipt.created) > 0 or len(receipt.reused) > 0 or len(receipt.skipped) > 0


class ClassroomPlannerGuestUpgradeHandler:
    """Preview and commit authenticated Klassrumskartan guest upgrades."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        seating_checkpoints: SeatingExportCheckpointRepositoryProtocol,
        grouping_checkpoints: GroupingExportCheckpointRepositoryProtocol,
        seating_export_jobs: SeatingExportJobRepositoryProtocol,
        grouping_export_jobs: GroupingExportJobRepositoryProtocol,
        guest_upgrade_repository: ClassroomPlannerGuestUpgradeRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._guest_upgrade_repository = guest_upgrade_repository
        self._clock = clock
        self._assets = GuestUpgradeAssetImporter(
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
            clock=clock,
            id_generator=id_generator,
        )
        self._history = GuestUpgradeHistoryImporter(
            drafts=drafts,
            seating_checkpoints=seating_checkpoints,
            grouping_checkpoints=grouping_checkpoints,
            seating_export_jobs=seating_export_jobs,
            grouping_export_jobs=grouping_export_jobs,
            guest_upgrade_repository=guest_upgrade_repository,
            clock=clock,
            id_generator=id_generator,
        )

    async def handle(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
    ) -> ClassroomPlannerGuestUpgradeReceipt:
        """Preview or commit one guest snapshot through the authenticated boundary."""

        snapshot = recompute_server_snapshot(request.snapshot)
        receipt = ClassroomPlannerGuestUpgradeReceipt(
            mode=request.mode,
            snapshot_id=snapshot.snapshot_id,
            schema_version=snapshot.schema_version,
            submitted_snapshot_content_hash=request.snapshot.snapshot_content_hash,
            server_snapshot_content_hash=snapshot.snapshot_content_hash,
        )
        if request.mode == "commit":
            async with self._uow:
                await self._process_snapshot(
                    owner_user_id=owner_user_id,
                    request=request,
                    snapshot=snapshot,
                    receipt=receipt,
                )
                if _receipt_consumed_meaningfully(receipt):
                    await self._guest_upgrade_repository.record_upgrade_consumption(
                        owner_user_id=owner_user_id,
                        app_id=APP_ID,
                        snapshot_id=snapshot.snapshot_id,
                        consumed_at=self._clock.now(),
                    )
            return receipt

        await self._process_snapshot(
            owner_user_id=owner_user_id,
            request=request,
            snapshot=snapshot,
            receipt=receipt,
        )
        return receipt

    async def _process_snapshot(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
    ) -> None:
        roster_cache, template_cache = await self._assets.import_assets(
            owner_user_id=owner_user_id,
            request=request,
            snapshot=snapshot,
            receipt=receipt,
        )
        imported_drafts = await self._history.import_drafts(
            owner_user_id=owner_user_id,
            request=request,
            snapshot=snapshot,
            receipt=receipt,
            roster_cache=roster_cache,
            template_cache=template_cache,
        )
        await self._history.import_checkpoints(
            owner_user_id=owner_user_id,
            request=request,
            snapshot=snapshot,
            receipt=receipt,
            roster_cache=roster_cache,
            template_cache=template_cache,
            imported_drafts=imported_drafts,
        )
