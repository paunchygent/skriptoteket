"""Protocols for classroom planner persistence seams.

These protocols let application handlers depend on typed planner aggregates
without coupling to SQLAlchemy. They cover teacher-owned reusable assets,
mutable draft workspaces, and immutable arrangement snapshots.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ArrangementSnapshot,
    DraftWorkspace,
    PlanDraft,
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

    async def save(self, *, draft: PlanDraft) -> None:
        """Save or update a draft root record."""
        ...

    async def save_workspace(self, *, workspace: DraftWorkspace) -> None:
        """Save or update a full draft workspace aggregate."""
        ...

    async def delete(self, *, draft_id: UUID) -> None:
        """Delete a draft root and cascade its workspace state."""
        ...


class ArrangementSnapshotRepositoryProtocol(Protocol):
    """Persist immutable arrangement snapshots."""

    async def get_by_id(self, *, snapshot_id: UUID) -> ArrangementSnapshot | None:
        """Load a snapshot by its unique id."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[ArrangementSnapshot]:
        """List snapshots owned by a specific user."""
        ...

    async def save(self, *, snapshot: ArrangementSnapshot) -> None:
        """Persist a new snapshot."""
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
