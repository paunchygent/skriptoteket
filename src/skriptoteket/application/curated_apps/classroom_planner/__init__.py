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
from .handlers.authenticated_shares import (
    CreateAuthenticatedGroupingShareHandler,
    CreateAuthenticatedSeatingShareHandler,
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
from .handlers.guest_upgrade_consumption import (
    GetClassroomPlannerGuestUpgradeConsumptionHandler,
)
from .handlers.public_grouping_export import RunPublicGroupingExportHandler
from .handlers.public_seating_export import RunPublicSeatingExportHandler
from .handlers.public_shares import (
    CreatePublicGuestGroupingShareHandler,
    CreatePublicGuestSeatingShareHandler,
    PublicGuestSharePolicy,
    PurgeExpiredPublicGuestShareArtifactsHandler,
    RevokePublicGuestShareHandler,
)
from .handlers.public_smart_grouping import RunPublicSmartGroupingHandler
from .handlers.public_smart_seating import RunPublicSmartSeatingHandler
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
from .handlers.share_artifacts import (
    BackfillClassroomPlannerSharePreviewsHandler,
    ClassroomPlannerShareLifecycleService,
    ClassroomPlannerSharePreviewBackfillResult,
    CreateClassroomPlannerShareArtifactCommand,
    CreateClassroomPlannerShareArtifactHandler,
    GetClassroomPlannerShareArtifactByTokenHandler,
    GetClassroomPlannerSharePreviewAssetHandler,
    ListClassroomPlannerShareArtifactsHandler,
    RevokeClassroomPlannerShareArtifactHandler,
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
from .shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
    RenderedClassroomPlannerShare,
)
from .smart_rule_diagnostic_contracts import (
    SmartRuleDiagnosticDto,
    serialize_smart_rule_diagnostics,
)

__all__ = [
    "AbandonDraftHandler",
    "ActivateGroupingHistoryDraftHandler",
    "ActivateSeatingHistoryDraftHandler",
    "BackfillClassroomPlannerSharePreviewsHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "CreateGroupingDraftHandler",
    "CreateGroupingExportJobHandler",
    "CreateSeatingDraftHandler",
    "CreateSeatingExportJobHandler",
    "ClassroomPlannerGuestUpgradeHandler",
    "ClassroomPlannerShareArtifact",
    "ClassroomPlannerShareArtifactCreateResult",
    "ClassroomPlannerShareArtifactSource",
    "ClassroomPlannerShareLifecycleService",
    "ClassroomPlannerSharePreviewAsset",
    "ClassroomPlannerSharePreviewBackfillResult",
    "CreateAuthenticatedGroupingShareHandler",
    "CreateAuthenticatedSeatingShareHandler",
    "CreateClassroomPlannerShareArtifactCommand",
    "CreateClassroomPlannerShareArtifactHandler",
    "CreatePublicGuestGroupingShareHandler",
    "CreatePublicGuestSeatingShareHandler",
    "GetClassroomPlannerGuestUpgradeConsumptionHandler",
    "GetClassroomPlannerShareArtifactByTokenHandler",
    "GetClassroomPlannerSharePreviewAssetHandler",
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
    "ListClassroomPlannerShareArtifactsHandler",
    "PatchDraftHandler",
    "PatchRosterSmartRulesHandler",
    "PrepareGroupingExportHandler",
    "PreparedGroupingExportContract",
    "PrepareSeatingExportHandler",
    "RunPublicSmartGroupingHandler",
    "RunPublicSmartSeatingHandler",
    "PreparedSeatingExportContract",
    "PublicGuestSharePolicy",
    "PurgeExpiredPublicGuestShareArtifactsHandler",
    "RevokePublicGuestShareHandler",
    "RunPublicGroupingExportHandler",
    "RedoDraftHandler",
    "RunPublicSeatingExportHandler",
    "RenderedClassroomPlannerShare",
    "ResolveDraftHandler",
    "RunSmartGroupingHandler",
    "RunSmartSeatingHandler",
    "SeatingExportKind",
    "SeatingExportLayoutId",
    "SeatingExportPaperSize",
    "SmartRuleDiagnosticDto",
    "RevokeClassroomPlannerShareArtifactHandler",
    "serialize_smart_rule_diagnostics",
    "UndoDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
]
