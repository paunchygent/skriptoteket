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
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
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
