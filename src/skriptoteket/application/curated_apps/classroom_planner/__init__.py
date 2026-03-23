"""Application handlers for the classroom planner curated app."""

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
from .handlers.grouping_history import (
    ActivateGroupingHistoryDraftHandler,
    DeleteHistoricGroupingDraftHandler,
)
from .handlers.rosters import (
    CreateRosterHandler,
    DeleteRosterHandler,
    GetRosterHandler,
    ListRostersHandler,
    UpdateRosterHandler,
)
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
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "CreateGroupingDraftHandler",
    "DeleteHistoricGroupingDraftHandler",
    "DeleteRoomTemplateHandler",
    "DeleteRosterHandler",
    "GetClassWorkspaceSummaryHandler",
    "GetDraftHandler",
    "GetDraftWorkspaceHandler",
    "GetResumableDraftHandler",
    "GetRoomTemplateHandler",
    "GetRosterHandler",
    "ListRoomTemplatesHandler",
    "ListRostersHandler",
    "PatchDraftHandler",
    "RedoDraftHandler",
    "ResolveDraftHandler",
    "UndoDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
]
