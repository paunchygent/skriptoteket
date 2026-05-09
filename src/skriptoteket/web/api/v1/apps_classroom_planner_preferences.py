"""Authenticated classroom planner preference loading for API routes.

Purpose:
    Translate backend-owned profile preferences into the classroom planner
    draft seed used when authenticated teachers create new seating or grouping
    drafts.

Relationships:
    - Called by authenticated classroom planner draft creation endpoints.
    - Delegates profile ownership to identity application handlers.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.draft_smart_preferences import (
    DraftSmartPreferenceSeed,
)
from skriptoteket.application.identity.commands import GetProfileCommand
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.identity import GetProfileHandlerProtocol


async def load_classroom_planner_smart_preference_seed(
    *,
    user: User,
    profile_handler: GetProfileHandlerProtocol,
) -> DraftSmartPreferenceSeed:
    result = await profile_handler.handle(GetProfileCommand(user_id=user.id))
    profile = result.profile
    return DraftSmartPreferenceSeed(
        smart_enabled=profile.classroom_planner_smart_enabled,
        use_history=profile.classroom_planner_use_history,
        grouping_seating_distance_enabled=(
            profile.classroom_planner_grouping_seating_distance_enabled
        ),
    )
