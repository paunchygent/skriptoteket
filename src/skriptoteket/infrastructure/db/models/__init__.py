"""SQLAlchemy model exports for metadata discovery and Alembic imports."""

from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    DraftGroupModel,
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
    StudentPlanningMetaModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import (
    RosterModel,
)
from skriptoteket.infrastructure.db.models.user_favorite import (
    UserFavoriteAppModel,
    UserFavoriteToolModel,
)

__all__ = [
    "DraftGroupModel",
    "GroupAssignmentModel",
    "PlanDraftModel",
    "RoomTemplateModel",
    "RosterModel",
    "SeatAssignmentModel",
    "StudentPlanningMetaModel",
    "UserFavoriteAppModel",
    "UserFavoriteToolModel",
]
