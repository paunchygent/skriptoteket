"""SQLAlchemy model exports for metadata discovery and Alembic imports."""

from skriptoteket.infrastructure.db.models.allowed_domain import AllowedDomainModel
from skriptoteket.infrastructure.db.models.blocked_domain import BlockedDomainModel
from skriptoteket.infrastructure.db.models.classroom_planner_grouping_export_checkpoint import (
    GroupingExportCheckpointModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_grouping_export_job import (
    GroupingExportJobModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_guest_upgrade_consumption import (
    ClassroomPlannerGuestUpgradeConsumptionModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    DraftGroupModel,
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import (
    RosterModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster_smart_rule import (
    RosterFixedSeatRuleModel,
    RosterRelationshipRuleModel,
    RosterSeatingPreferenceModel,
    RosterSmartRuleSetModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_checkpoint import (
    SeatingExportCheckpointModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_job import (
    SeatingExportJobModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_webhook_binding import (
    SeatingExportWebhookBindingModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
)
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.identity_projection import (
    IdentityProjectionEventModel,
    IdentityProjectionModel,
)
from skriptoteket.infrastructure.db.models.password_reset_token import PasswordResetTokenModel
from skriptoteket.infrastructure.db.models.user_favorite import (
    UserFavoriteAppModel,
    UserFavoriteToolModel,
)

__all__ = [
    "AllowedDomainModel",
    "BlockedDomainModel",
    "ClassroomPlannerGuestUpgradeConsumptionModel",
    "ClassroomPlannerShareArtifactModel",
    "DraftGroupModel",
    "ConversionHubJobModel",
    "GroupingExportCheckpointModel",
    "GroupingExportJobModel",
    "GroupAssignmentModel",
    "IdentityProjectionEventModel",
    "IdentityProjectionModel",
    "PlanDraftModel",
    "PasswordResetTokenModel",
    "RosterFixedSeatRuleModel",
    "RosterRelationshipRuleModel",
    "RoomTemplateModel",
    "RosterModel",
    "RosterSeatingPreferenceModel",
    "RosterSmartRuleSetModel",
    "SeatAssignmentModel",
    "SeatingExportCheckpointModel",
    "SeatingExportJobModel",
    "SeatingExportWebhookBindingModel",
    "UserFavoriteAppModel",
    "UserFavoriteToolModel",
]
