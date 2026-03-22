"""Owner-scoped roster and template loading for planner handlers.

This module centralizes the access checks shared by classroom-planner
application handlers. It keeps handler classes focused on lifecycle behavior
while ensuring roster and room-template lookups stay owner-scoped and
consistent across grouping and seating flows.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Roster
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)


async def load_roster_and_template_for_owner(
    *,
    rosters: RosterRepositoryProtocol,
    templates: RoomTemplateRepositoryProtocol,
    owner_user_id: UUID,
    roster_id: UUID,
    template_id: UUID | None = None,
) -> tuple[Roster, RoomTemplate | None]:
    """Load owner-scoped roster and optional template for planner lifecycle work."""

    roster = await rosters.get_by_id(roster_id=roster_id)
    if not roster or roster.owner_user_id != owner_user_id:
        raise not_found("Roster", str(roster_id))

    template = None
    if template_id is not None:
        template = await templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

    return roster, template
