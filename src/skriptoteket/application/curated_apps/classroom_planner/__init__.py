"""Application handlers for the classroom planner curated app."""

from .handlers.bootstrap import GetBootstrapHandler
from .handlers.drafts import (
    AbandonDraftHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetResumableDraftHandler,
    PatchDraftHandler,
    ResolveDraftHandler,
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
    "AbandonDraftHandler",
    "ApplySuggestionHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "DeleteRoomTemplateHandler",
    "DeleteRosterHandler",
    "FinalizeDraftHandler",
    "GenerateSuggestionsHandler",
    "GetBootstrapHandler",
    "GetDraftHandler",
    "GetDraftWorkspaceHandler",
    "GetResumableDraftHandler",
    "GetRoomTemplateHandler",
    "GetRosterHandler",
    "GetSnapshotHandler",
    "ListRoomTemplatesHandler",
    "ListRostersHandler",
    "ListSnapshotsHandler",
    "PatchDraftHandler",
    "RandomizeDraftHandler",
    "ResolveDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
    "ValidateDraftHandler",
]
