"""History persistence helpers for Klassrumskartan plan drafts.

Draft history snapshots share the same child-row tables as live workspaces.
The helper replaces related collections safely and applies bounded undo/redo
snapshots without broadening the plan-draft repository class.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftWorkspace,
    PlanDraftKind,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    DraftGroupModel,
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
)
from skriptoteket.infrastructure.repositories.classroom_planner_plan_draft_mapping import (
    create_workspace_snapshot,
)


class PlanDraftHistoryPersistence:
    """Persist bounded history snapshots and related draft collections."""

    def __init__(self, *, session: AsyncSession, history_limit: int) -> None:
        self._session = session
        self._history_limit = history_limit

    async def replace_related_collection(
        self,
        *,
        model: PlanDraftModel,
        attribute_name: str,
        new_items: list[object],
    ) -> None:
        """Replace child rows without tripping natural-key uniqueness constraints."""
        existing_items = list(await getattr(model.awaitable_attrs, attribute_name))
        if existing_items:
            getattr(model, attribute_name).clear()
            await self._session.flush()
        getattr(model, attribute_name).extend(new_items)

    async def push_history(self, *, model: PlanDraftModel, workspace: DraftWorkspace) -> None:
        """Push a new snapshot to the bounded draft history stack."""
        snapshot = create_workspace_snapshot(workspace)

        history = (model.history_stack or []).copy()
        undo_index = model.undo_index if model.undo_index is not None else 0
        history = history[: undo_index + 1]

        if not history or history[-1] != snapshot:
            history.append(snapshot)
            history = history[-self._history_limit :]
            model.history_stack = history
            model.undo_index = len(history) - 1

    async def apply_snapshot(
        self,
        *,
        model: PlanDraftModel,
        snapshot: dict[str, Any],
    ) -> None:
        """Apply a historical snapshot to the active draft model."""
        if model.draft_kind == PlanDraftKind.GROUPING.value:
            template_id = snapshot.get("template_id")
            model.template_id = UUID(str(template_id)) if template_id else None
        model.smart_enabled = bool(snapshot.get("smart_enabled", False))
        model.use_history = bool(snapshot.get("use_history", False))
        model.grouping_seating_distance_enabled = bool(
            snapshot.get("grouping_seating_distance_enabled", False)
        )

        await self.replace_related_collection(
            model=model,
            attribute_name="groups",
            new_items=[
                DraftGroupModel(
                    group_id=group["id"],
                    name=group["name"],
                    sort_order=group["sort_order"],
                    name_is_custom=group.get("name_is_custom", False),
                )
                for group in cast(list[dict[str, Any]], snapshot["groups"])
            ],
        )
        await self.replace_related_collection(
            model=model,
            attribute_name="group_assignments",
            new_items=[
                GroupAssignmentModel(
                    student_id=assignment["student_id"],
                    group_id=assignment["group_id"],
                )
                for assignment in cast(list[dict[str, Any]], snapshot["group_assignments"])
            ],
        )
        await self.replace_related_collection(
            model=model,
            attribute_name="seat_assignments",
            new_items=[
                SeatAssignmentModel(
                    student_id=assignment["student_id"],
                    seat_id=assignment["seat_id"],
                )
                for assignment in cast(list[dict[str, Any]], snapshot.get("seat_assignments", []))
            ],
        )
        if model.revision is None:
            model.revision = 1
        else:
            model.revision += 1
