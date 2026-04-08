"""SQLAlchemy guest-upgrade lookup repository for Klassrumskartan.

Purpose:
    Provide the import-specific lookup helpers needed by the authenticated
    guest-upgrade flow while keeping the main planner repositories focused on
    their normal CRUD and history responsibilities.

Relationships:
    - Implements `ClassroomPlannerGuestUpgradeRepositoryProtocol`.
    - Reads planner drafts plus export-backed checkpoint tables.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
)
from skriptoteket.infrastructure.db.models.classroom_planner_grouping_export_checkpoint import (
    GroupingExportCheckpointModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_guest_upgrade_consumption import (
    ClassroomPlannerGuestUpgradeConsumptionModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import PlanDraftModel
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_checkpoint import (
    SeatingExportCheckpointModel,
)
from skriptoteket.protocols.classroom_planner_guest_upgrade import (
    ClassroomPlannerGuestUpgradeRepositoryProtocol,
)


class PostgreSQLClassroomPlannerGuestUpgradeRepository(
    ClassroomPlannerGuestUpgradeRepositoryProtocol
):
    """Read import-identity and checkpoint-dedupe facts for guest upgrades."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_draft(model: PlanDraftModel) -> PlanDraft:
        return PlanDraft(
            id=model.id,
            owner_user_id=model.owner_user_id,
            roster_id=model.roster_id,
            draft_kind=PlanDraftKind(model.draft_kind),
            template_id=model.template_id,
            task_entry_classroom_selection_mode=ClassroomSelectionMode(
                model.task_entry_classroom_selection_mode
            ),
            smart_enabled=model.smart_enabled,
            use_history=model.use_history,
            grouping_seating_distance_enabled=model.grouping_seating_distance_enabled,
            status=PlanDraftStatus(model.status),
            guest_import_identity=model.guest_import_identity,
            revision=model.revision,
            last_opened_at=model.last_opened_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def has_consumed_upgrade(
        self,
        *,
        owner_user_id: UUID,
        app_id: str,
    ) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    ClassroomPlannerGuestUpgradeConsumptionModel.owner_user_id == owner_user_id,
                    ClassroomPlannerGuestUpgradeConsumptionModel.app_id == app_id,
                )
            )
        )
        return bool(result.scalar())

    async def record_upgrade_consumption(
        self,
        *,
        owner_user_id: UUID,
        app_id: str,
        snapshot_id: str,
        consumed_at: datetime,
    ) -> None:
        await self._session.execute(
            insert(ClassroomPlannerGuestUpgradeConsumptionModel)
            .values(
                owner_user_id=owner_user_id,
                app_id=app_id,
                snapshot_id=snapshot_id,
                consumed_at=consumed_at,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ClassroomPlannerGuestUpgradeConsumptionModel.owner_user_id,
                    ClassroomPlannerGuestUpgradeConsumptionModel.app_id,
                ]
            )
        )

    async def get_imported_draft_by_identity(
        self,
        *,
        owner_user_id: UUID,
        guest_import_identity: str,
    ) -> PlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel).where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.guest_import_identity == guest_import_identity,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_draft(model) if model is not None else None

    async def grouping_checkpoint_exists(
        self,
        *,
        roster_id: UUID,
        assignment_hash: str,
    ) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    GroupingExportCheckpointModel.roster_id == roster_id,
                    GroupingExportCheckpointModel.assignment_hash == assignment_hash,
                )
            )
        )
        return bool(result.scalar())

    async def seating_checkpoint_exists(
        self,
        *,
        roster_id: UUID,
        room_context_hash: str,
        assignment_hash: str,
    ) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    SeatingExportCheckpointModel.roster_id == roster_id,
                    SeatingExportCheckpointModel.room_context_hash == room_context_hash,
                    SeatingExportCheckpointModel.assignment_hash == assignment_hash,
                )
            )
        )
        return bool(result.scalar())
