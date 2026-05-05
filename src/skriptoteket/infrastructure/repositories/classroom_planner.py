"""PostgreSQL plan-draft repository for Klassrumskartan.

Plan drafts hold the mutable grouping and seating workspaces. Roster and room
template repositories live in focused sibling modules and are re-exported here
for existing import paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import delete, exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassWorkspaceDraftSummary,
    DraftWorkspace,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    ResumablePlanDraft,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    DraftGroupModel,
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.infrastructure.repositories.classroom_planner_plan_draft_history import (
    PlanDraftHistoryPersistence,
)
from skriptoteket.infrastructure.repositories.classroom_planner_plan_draft_mapping import (
    to_draft,
    to_draft_summary,
    to_workspace,
)
from skriptoteket.infrastructure.repositories.classroom_planner_room_templates import (
    PostgreSQLRoomTemplateRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_rosters import (
    PostgreSQLRosterRepository,
)
from skriptoteket.protocols.classroom_planner import PlanDraftRepositoryProtocol

__all__ = [
    "PostgreSQLPlanDraftRepository",
    "PostgreSQLRoomTemplateRepository",
    "PostgreSQLRosterRepository",
]


class PostgreSQLPlanDraftRepository(PlanDraftRepositoryProtocol):
    """Persist draft roots and fundamentals workspace state in PostgreSQL."""

    _HISTORY_LIMIT = 10

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._history = PlanDraftHistoryPersistence(
            session=session,
            history_limit=self._HISTORY_LIMIT,
        )

    async def get_by_id(self, *, draft_id: UUID) -> PlanDraft | None:
        model = await self._session.get(PlanDraftModel, draft_id)
        return to_draft(model) if model else None

    async def get_workspace(self, *, draft_id: UUID) -> DraftWorkspace | None:
        result = await self._session.execute(
            select(PlanDraftModel)
            .options(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
            )
            .where(PlanDraftModel.id == draft_id)
        )
        model = result.scalar_one_or_none()
        return to_workspace(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[PlanDraft]:
        result = await self._session.execute(
            select(PlanDraftModel)
            .where(PlanDraftModel.owner_user_id == owner_user_id)
            .order_by(PlanDraftModel.updated_at.desc())
        )
        return [to_draft(model) for model in result.scalars().all()]

    async def get_active_by_roster_and_kind(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> PlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return to_draft(model) if model else None

    async def acquire_roster_kind_lifecycle_lock(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> None:
        lock_source = f"{owner_user_id}:{roster_id}:{draft_kind.value}".encode("utf-8")
        lock_key = int.from_bytes(blake2b(lock_source, digest_size=8).digest(), "big")
        lock_key &= 0x7FFFFFFFFFFFFFFF
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    async def get_latest_resumable(self, *, owner_user_id: UUID) -> ResumablePlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel, RosterModel.name, RoomTemplateModel.name)
            .join(RosterModel, RosterModel.id == PlanDraftModel.roster_id)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        model, roster_name, template_name = row
        return ResumablePlanDraft(
            draft=to_draft(model),
            roster_name=roster_name,
            template_name=template_name,
        )

    async def _get_latest_summary_for_kind_and_status(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
        status: PlanDraftStatus,
    ) -> PlanDraftSummary | None:
        """Load the latest compact summary for one class, task, and lifecycle status."""

        result = await self._session.execute(
            select(PlanDraftModel, RoomTemplateModel.name)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status == status.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        model, template_name = row
        return to_draft_summary(model, template_name=template_name)

    async def _list_history_summaries_for_kind(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
        limit: int,
    ) -> list[PlanDraftSummary]:
        """Load compact history summaries for one class and task kind."""

        result = await self._session.execute(
            select(PlanDraftModel, RoomTemplateModel.name)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status != PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(limit)
        )
        return [
            to_draft_summary(model, template_name=template_name)
            for model, template_name in result.all()
        ]

    async def get_class_workspace_draft_summary(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        history_limit_per_kind: int = 5,
    ) -> ClassWorkspaceDraftSummary:
        return ClassWorkspaceDraftSummary(
            active_grouping_draft=await self._get_latest_summary_for_kind_and_status(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
                status=PlanDraftStatus.ACTIVE,
            ),
            active_seating_draft=await self._get_latest_summary_for_kind_and_status(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.SEATING,
                status=PlanDraftStatus.ACTIVE,
            ),
            grouping_history=await self._list_history_summaries_for_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
                limit=history_limit_per_kind,
            ),
            seating_history=await self._list_history_summaries_for_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.SEATING,
                limit=history_limit_per_kind,
            ),
        )

    async def has_active_for_roster(self, *, owner_user_id: UUID, roster_id: UUID) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    PlanDraftModel.owner_user_id == owner_user_id,
                    PlanDraftModel.roster_id == roster_id,
                    PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
                )
            )
        )
        return bool(result.scalar())

    async def has_active_for_template(self, *, owner_user_id: UUID, template_id: UUID) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    PlanDraftModel.owner_user_id == owner_user_id,
                    PlanDraftModel.template_id == template_id,
                    PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
                )
            )
        )
        return bool(result.scalar())

    async def delete_for_roster(self, *, owner_user_id: UUID, roster_id: UUID) -> None:
        await self._session.execute(
            delete(PlanDraftModel).where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
            )
        )
        await self._session.flush()

    async def delete_for_template(self, *, owner_user_id: UUID, template_id: UUID) -> None:
        await self._session.execute(
            delete(PlanDraftModel).where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.template_id == template_id,
            )
        )
        await self._session.flush()

    async def save(self, *, draft: PlanDraft) -> None:
        model = await self._session.get(PlanDraftModel, draft.id)
        if model:
            model.roster_id = draft.roster_id
            model.draft_kind = draft.draft_kind.value
            model.template_id = draft.template_id
            model.task_entry_classroom_selection_mode = (
                draft.task_entry_classroom_selection_mode.value
            )
            model.smart_enabled = draft.smart_enabled
            model.use_history = draft.use_history
            model.grouping_seating_distance_enabled = draft.grouping_seating_distance_enabled
            model.status = draft.status.value
            model.guest_import_identity = draft.guest_import_identity
            model.revision = draft.revision
            model.last_opened_at = draft.last_opened_at
            model.updated_at = draft.updated_at
        else:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                draft_kind=draft.draft_kind.value,
                template_id=draft.template_id,
                task_entry_classroom_selection_mode=(
                    draft.task_entry_classroom_selection_mode.value
                ),
                smart_enabled=draft.smart_enabled,
                use_history=draft.use_history,
                grouping_seating_distance_enabled=draft.grouping_seating_distance_enabled,
                status=draft.status.value,
                guest_import_identity=draft.guest_import_identity,
                revision=draft.revision,
                last_opened_at=draft.last_opened_at,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def save_workspace(self, *, workspace: DraftWorkspace) -> None:
        draft = workspace.draft
        model = await self._session.get(
            PlanDraftModel,
            draft.id,
            options=(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
            ),
        )

        previous_workspace = None
        reset_history_for_seating_context = (
            model is not None
            and draft.draft_kind == PlanDraftKind.SEATING
            and model.template_id != draft.template_id
        )
        if model is not None and not model.history_stack and not reset_history_for_seating_context:
            previous_workspace = to_workspace(model)

        if model is None:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                draft_kind=draft.draft_kind.value,
                template_id=draft.template_id,
                task_entry_classroom_selection_mode=(
                    draft.task_entry_classroom_selection_mode.value
                ),
                smart_enabled=draft.smart_enabled,
                use_history=draft.use_history,
                grouping_seating_distance_enabled=draft.grouping_seating_distance_enabled,
                status=draft.status.value,
                guest_import_identity=draft.guest_import_identity,
                revision=draft.revision,
                last_opened_at=draft.last_opened_at,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        else:
            model.roster_id = draft.roster_id
            model.draft_kind = draft.draft_kind.value
            model.template_id = draft.template_id
            model.task_entry_classroom_selection_mode = (
                draft.task_entry_classroom_selection_mode.value
            )
            model.smart_enabled = draft.smart_enabled
            model.use_history = draft.use_history
            model.grouping_seating_distance_enabled = draft.grouping_seating_distance_enabled
            model.status = draft.status.value
            model.guest_import_identity = draft.guest_import_identity
            model.revision = draft.revision
            model.last_opened_at = draft.last_opened_at
            model.updated_at = draft.updated_at

        await self._history.replace_related_collection(
            model=model,
            attribute_name="groups",
            new_items=[
                DraftGroupModel(
                    group_id=group.id,
                    name=group.name,
                    sort_order=group.sort_order,
                    name_is_custom=group.name_is_custom,
                )
                for group in workspace.groups
            ],
        )
        await self._history.replace_related_collection(
            model=model,
            attribute_name="group_assignments",
            new_items=[
                GroupAssignmentModel(student_id=assignment.student_id, group_id=assignment.group_id)
                for assignment in workspace.group_assignments
            ],
        )
        await self._history.replace_related_collection(
            model=model,
            attribute_name="seat_assignments",
            new_items=[
                SeatAssignmentModel(student_id=assignment.student_id, seat_id=assignment.seat_id)
                for assignment in workspace.seat_assignments
            ],
        )
        if reset_history_for_seating_context:
            model.history_stack = []
            model.undo_index = 0
        elif previous_workspace is not None:
            await self._history.push_history(model=model, workspace=previous_workspace)
        await self._history.push_history(model=model, workspace=workspace)

        await self._session.flush()

    async def undo(self, *, draft_id: UUID) -> DraftWorkspace | None:
        """Step backward in the bounded draft history stack."""

        model = await self._session.get(
            PlanDraftModel,
            draft_id,
            options=(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
            ),
        )
        if model is None or not model.history_stack or model.undo_index <= 0:
            return None

        model.undo_index -= 1
        snapshot = model.history_stack[model.undo_index]
        await self._history.apply_snapshot(model=model, snapshot=snapshot)
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

        return to_workspace(model)

    async def redo(self, *, draft_id: UUID) -> DraftWorkspace | None:
        """Step forward in the bounded draft history stack."""

        model = await self._session.get(
            PlanDraftModel,
            draft_id,
            options=(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
            ),
        )
        if (
            model is None
            or not model.history_stack
            or model.undo_index >= len(model.history_stack) - 1
        ):
            return None

        model.undo_index += 1
        snapshot = model.history_stack[model.undo_index]
        await self._history.apply_snapshot(model=model, snapshot=snapshot)
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

        return to_workspace(model)

    async def mark_status(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        status: PlanDraftStatus,
        updated_at: datetime,
    ) -> PlanDraft | None:
        model = await self._session.get(PlanDraftModel, draft_id)
        if model is None or model.owner_user_id != owner_user_id:
            return None
        model.status = status.value
        model.updated_at = updated_at
        await self._session.flush()
        return to_draft(model)

    async def delete(self, *, draft_id: UUID) -> None:
        await self._session.execute(delete(PlanDraftModel).where(PlanDraftModel.id == draft_id))
        await self._session.flush()
