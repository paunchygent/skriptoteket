from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.apps.classroom_planner.models import RoomTemplate, Roster


class RosterRepositoryProtocol(Protocol):
    """Protocol for Roster persistence."""

    async def get_by_id(self, *, roster_id: UUID) -> Roster | None:
        """Loads a roster by its unique ID."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[Roster]:
        """Lists all rosters owned by a specific user."""
        ...

    async def save(self, *, roster: Roster) -> None:
        """Saves or updates a roster."""
        ...

    async def delete(self, *, roster_id: UUID) -> None:
        """Deletes a roster."""
        ...


class RoomTemplateRepositoryProtocol(Protocol):
    """Protocol for RoomTemplate persistence."""

    async def get_by_id(self, *, template_id: UUID) -> RoomTemplate | None:
        """Loads a room template by its unique ID."""
        ...

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        """Lists all room templates owned by a specific user."""
        ...

    async def save(self, *, template: RoomTemplate) -> None:
        """Saves or updates a room template."""
        ...

    async def delete(self, *, template_id: UUID) -> None:
        """Deletes a room template."""
        ...
