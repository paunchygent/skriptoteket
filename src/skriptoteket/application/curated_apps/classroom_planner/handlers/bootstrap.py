"""Bootstrap handlers for the classroom planner curated app.

This module provides the bespoke app bootstrap payload consumed by the SPA. The
bootstrap response is the authoritative source for lesson modes and feature
flags used by the rest of the planner workflow.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    LESSON_MODE_PRESETS,
    ClassroomPlannerBootstrapPayload,
)


class GetBootstrapHandler:
    """Return app initialization metadata for the classroom planner."""

    async def handle(self, *, owner_user_id: UUID) -> ClassroomPlannerBootstrapPayload:
        del owner_user_id
        return ClassroomPlannerBootstrapPayload(
            lesson_modes=list(LESSON_MODE_PRESETS),
            feature_flags={
                "solver_v1": True,
                "multi_room_support": False,
                "randomizer_v1": True,
                "history_rules_v1": False,
            },
        )
