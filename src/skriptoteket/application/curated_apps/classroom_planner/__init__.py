"""Application handlers for the classroom planner curated app."""

from .handlers.bootstrap import GetBootstrapHandler
from .handlers.drafts import (
    CreateDraftHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    PatchDraftHandler,
)
from .handlers.planning import (
    ApplySuggestionHandler,
    FinalizeDraftHandler,
    GenerateSuggestionsHandler,
    GetSnapshotHandler,
    ListSnapshotsHandler,
    RandomizeDraftHandler,
    ValidateDraftHandler,
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

__all__ = [
    "ApplySuggestionHandler",
    "CreateDraftHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "DeleteRoomTemplateHandler",
    "DeleteRosterHandler",
    "FinalizeDraftHandler",
    "GenerateSuggestionsHandler",
    "GetBootstrapHandler",
    "GetDraftHandler",
    "GetDraftWorkspaceHandler",
    "GetRoomTemplateHandler",
    "GetRosterHandler",
    "GetSnapshotHandler",
    "ListRoomTemplatesHandler",
    "ListRostersHandler",
    "ListSnapshotsHandler",
    "PatchDraftHandler",
    "RandomizeDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
    "ValidateDraftHandler",
]
