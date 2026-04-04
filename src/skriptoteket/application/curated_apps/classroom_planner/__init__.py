"""Application handlers for the classroom planner curated app."""

from .exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from .handlers.drafts import (
    AbandonDraftHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetResumableDraftHandler,
    PatchDraftHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    UndoDraftHandler,
)
from .handlers.grouping_drafts import CreateGroupingDraftHandler
from .handlers.grouping_export_job_completion import GroupingExportJobFinalizer
from .handlers.grouping_export_jobs import (
    CreateGroupingExportJobHandler,
    DownloadGroupingExportJobHandler,
    GetGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
)
from .handlers.grouping_exports import PrepareGroupingExportHandler
from .handlers.grouping_history import (
    ActivateGroupingHistoryDraftHandler,
    DeleteHistoricGroupingDraftHandler,
)
from .handlers.guest_upgrade import ClassroomPlannerGuestUpgradeHandler
from .handlers.rosters import (
    CreateRosterHandler,
    DeleteRosterHandler,
    GetRosterHandler,
    ListRostersHandler,
    UpdateRosterHandler,
)
from .handlers.seating_drafts import CreateSeatingDraftHandler
from .handlers.seating_export_job_completion import (
    DownloadSeatingExportJobHandler,
    SeatingExportJobFinalizer,
)
from .handlers.seating_export_jobs import (
    CreateSeatingExportJobHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetSeatingExportJobHandler,
)
from .handlers.seating_exports import PrepareSeatingExportHandler
from .handlers.seating_history import (
    ActivateSeatingHistoryDraftHandler,
    DeleteHistoricSeatingDraftHandler,
)
from .handlers.smart_grouping import RunSmartGroupingHandler
from .handlers.smart_rules import (
    GetRosterSmartRulesHandler,
    PatchRosterSmartRulesHandler,
)
from .handlers.smart_seating import RunSmartSeatingHandler
from .handlers.templates import (
    CreateRoomTemplateHandler,
    DeleteRoomTemplateHandler,
    GetRoomTemplateHandler,
    ListRoomTemplatesHandler,
    UpdateRoomTemplateHandler,
)
from .handlers.workspace_summary import GetClassWorkspaceSummaryHandler

__all__ = [
    "AbandonDraftHandler",
    "ActivateGroupingHistoryDraftHandler",
    "ActivateSeatingHistoryDraftHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "CreateGroupingDraftHandler",
    "CreateGroupingExportJobHandler",
    "CreateSeatingDraftHandler",
    "CreateSeatingExportJobHandler",
    "ClassroomPlannerGuestUpgradeHandler",
    "DeleteHistoricGroupingDraftHandler",
    "DeleteHistoricSeatingDraftHandler",
    "DeleteRoomTemplateHandler",
    "DeleteRosterHandler",
    "DownloadGroupingExportJobHandler",
    "DownloadSeatingExportJobHandler",
    "GroupingExportJobFinalizer",
    "SeatingExportJobFinalizer",
    "GetClassWorkspaceSummaryHandler",
    "GetDraftHandler",
    "GetDraftWorkspaceHandler",
    "GetResumableDraftHandler",
    "GetRoomTemplateHandler",
    "GetRosterHandler",
    "GetRecoverableSeatingExportJobForDraftHandler",
    "GetRecoverableGroupingExportJobForDraftHandler",
    "GetRosterSmartRulesHandler",
    "GetSeatingExportJobHandler",
    "GetGroupingExportJobHandler",
    "GroupingExportKind",
    "GroupingExportPaperSize",
    "ListRoomTemplatesHandler",
    "ListRostersHandler",
    "PatchDraftHandler",
    "PatchRosterSmartRulesHandler",
    "PrepareGroupingExportHandler",
    "PreparedGroupingExportContract",
    "PrepareSeatingExportHandler",
    "PreparedSeatingExportContract",
    "RedoDraftHandler",
    "ResolveDraftHandler",
    "RunSmartGroupingHandler",
    "RunSmartSeatingHandler",
    "SeatingExportKind",
    "SeatingExportLayoutId",
    "SeatingExportPaperSize",
    "UndoDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
]
