"""Seating-history lifecycle handlers for the classroom planner.

This module owns historic seating-draft transitions that sit one level above
future in-draft undo/redo. It lets the SPA reactivate a superseded seating
draft as the new current draft for a class and remove historical seating
drafts without exposing destructive controls for the active workspace.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.classroom_planner import PlanDraftRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


async def _get_owned_seating_draft(
    *,
    drafts: PlanDraftRepositoryProtocol,
    draft_id: UUID,
    owner_user_id: UUID,
) -> PlanDraft:
    """Load one owner-scoped seating draft or raise not found."""

    draft = await drafts.get_by_id(draft_id=draft_id)
    if (
        draft is None
        or draft.owner_user_id != owner_user_id
        or draft.draft_kind != PlanDraftKind.SEATING
    ):
        raise not_found("PlanDraft", str(draft_id))
    return draft


class ActivateSeatingHistoryDraftHandler:
    """Promote one historical seating draft to the active class draft."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._clock = clock

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> PlanDraft:
        target = await _get_owned_seating_draft(
            drafts=self._drafts,
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )

        now = self._clock.now()
        async with self._uow:
            await self._drafts.acquire_roster_kind_lifecycle_lock(
                owner_user_id=owner_user_id,
                roster_id=target.roster_id,
                draft_kind=PlanDraftKind.SEATING,
            )
            current_target = await _get_owned_seating_draft(
                drafts=self._drafts,
                draft_id=draft_id,
                owner_user_id=owner_user_id,
            )
            current_active = await self._drafts.get_active_by_roster_and_kind(
                owner_user_id=owner_user_id,
                roster_id=current_target.roster_id,
                draft_kind=PlanDraftKind.SEATING,
            )
            if current_active is not None and current_active.id != current_target.id:
                await self._drafts.save(
                    draft=current_active.model_copy(
                        update={
                            "status": PlanDraftStatus.SUPERSEDED,
                            "updated_at": now,
                        }
                    )
                )

            activated = current_target.model_copy(
                update={
                    "status": PlanDraftStatus.ACTIVE,
                    "last_opened_at": now,
                    "updated_at": now,
                }
            )
            await self._drafts.save(draft=activated)
            return activated


class DeleteHistoricSeatingDraftHandler:
    """Delete one historic seating draft while protecting the active draft."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> None:
        target = await _get_owned_seating_draft(
            drafts=self._drafts,
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        if target.status == PlanDraftStatus.ACTIVE:
            raise validation_error("Det aktiva sittschemat kan inte tas bort från historiken.")

        async with self._uow:
            await self._drafts.acquire_roster_kind_lifecycle_lock(
                owner_user_id=owner_user_id,
                roster_id=target.roster_id,
                draft_kind=PlanDraftKind.SEATING,
            )
            current_target = await _get_owned_seating_draft(
                drafts=self._drafts,
                draft_id=draft_id,
                owner_user_id=owner_user_id,
            )
            if current_target.status == PlanDraftStatus.ACTIVE:
                raise validation_error("Det aktiva sittschemat kan inte tas bort från historiken.")
            await self._drafts.delete(draft_id=draft_id)
