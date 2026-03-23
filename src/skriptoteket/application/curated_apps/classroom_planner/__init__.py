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
from .handlers.seating_drafts import CreateSeatingDraftHandler
from .handlers.seating_history import (
    ActivateSeatingHistoryDraftHandler,
    DeleteHistoricSeatingDraftHandler,
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
    "ActivateSeatingHistoryDraftHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "CreateGroupingDraftHandler",
    "CreateSeatingDraftHandler",
    "DeleteHistoricGroupingDraftHandler",
    "DeleteHistoricSeatingDraftHandler",
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
