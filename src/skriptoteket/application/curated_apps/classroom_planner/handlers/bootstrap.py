from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerBootstrapPayload,
    LessonModePreset,
)

# Standard presets
LESSON_MODES = [
    LessonModePreset(id="seating", name="Sittplatsschema"),
    LessonModePreset(id="group_work", name="Gruppering"),
]


class GetBootstrapHandler:
    """Handler to return the initial payload for app initialization."""

    async def handle(self, *, owner_user_id: UUID) -> ClassroomPlannerBootstrapPayload:
        return ClassroomPlannerBootstrapPayload(
            lesson_modes=LESSON_MODES,
            feature_flags={
                "solver_v1": False,
                "multi_room_support": False,
            },
        )
