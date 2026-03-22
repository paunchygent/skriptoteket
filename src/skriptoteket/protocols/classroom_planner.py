"""Protocols for classroom planner persistence seams.

These protocols let application handlers depend on typed planner aggregates
without coupling to SQLAlchemy. They cover teacher-owned reusable assets and
mutable draft workspaces for the active grouping, seating, and note workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassWorkspaceDraftSummary,
    DraftWorkspace,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    ResumablePlanDraft,
    RoomTemplate,
    Roster,
)


class PlanDraftRepositoryProtocol(Protocol):
    """Persist mutable planner drafts and their workspace state."""

    async def get_by_id(self, *, draft_id: UUID) -> PlanDraft | None:
        """Load a draft root by its unique id."""
        ...

    async def get_workspace(self, *, draft_id: UUID) -> DraftWorkspace | None:
        """Load a draft and all draft-scoped planning state."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[PlanDraft]:
        """List draft roots owned by a specific user."""
        ...

    async def get_active_by_roster_and_kind(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> PlanDraft | None:
        """Load the current active draft for one class and draft kind."""
        ...

    async def acquire_roster_kind_lifecycle_lock(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> None:
        """Serialize lifecycle transitions for one class and draft kind."""
        ...

    async def get_latest_resumable(self, *, owner_user_id: UUID) -> ResumablePlanDraft | None:
        """Load the latest resumable draft plus landing-page display labels."""
        ...

    async def get_class_workspace_draft_summary(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        history_limit_per_kind: int = 5,
    ) -> ClassWorkspaceDraftSummary:
        """Load active and historical draft summaries for one class."""
        ...

    async def has_active_for_roster(self, *, owner_user_id: UUID, roster_id: UUID) -> bool:
        """Return whether an active draft still depends on a roster."""
        ...

    async def has_active_for_template(self, *, owner_user_id: UUID, template_id: UUID) -> bool:
        """Return whether an active draft still depends on a room template."""
        ...

    async def save(self, *, draft: PlanDraft) -> None:
        """Save or update a draft root record."""
        ...

    async def save_workspace(self, *, workspace: DraftWorkspace) -> None:
        """Save or update a full draft workspace aggregate."""
        ...

    async def undo(self, *, draft_id: UUID) -> DraftWorkspace | None:
        """Step backward in the grouping history stack."""
        ...

    async def redo(self, *, draft_id: UUID) -> DraftWorkspace | None:
        """Step forward in the grouping history stack."""
        ...

    async def mark_status(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        status: PlanDraftStatus,
        updated_at: datetime,
    ) -> PlanDraft | None:
        """Update the lifecycle status for one owner-scoped draft."""
        ...

    async def delete(self, *, draft_id: UUID) -> None:
        """Delete a draft root and cascade its workspace state."""
        ...


class RosterRepositoryProtocol(Protocol):
    """Persist reusable rosters."""

    async def get_by_id(self, *, roster_id: UUID) -> Roster | None:
        """Load a roster by its unique id."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[Roster]:
        """List all rosters owned by a specific user."""
        ...

    async def save(self, *, roster: Roster) -> None:
        """Save or update a roster."""
        ...

    async def delete(self, *, roster_id: UUID) -> None:
        """Delete a roster."""
        ...


class RoomTemplateRepositoryProtocol(Protocol):
    """Persist reusable room templates."""

    async def get_by_id(self, *, template_id: UUID) -> RoomTemplate | None:
        """Load a room template by its unique id."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        """List all room templates owned by a specific user."""
        ...

    async def save(self, *, template: RoomTemplate) -> None:
        """Save or update a room template."""
        ...

    async def delete(self, *, template_id: UUID) -> None:
        """Delete a room template."""
        ...
