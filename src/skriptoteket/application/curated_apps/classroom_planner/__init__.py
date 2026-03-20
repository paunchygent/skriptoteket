"""Classroom Planner application handlers."""

from .handlers.bootstrap import GetBootstrapHandler
from .handlers.drafts import CreateDraftHandler, GetDraftHandler, PatchDraftHandler
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
    "CreateDraftHandler",
    "CreateRoomTemplateHandler",
    "CreateRosterHandler",
    "DeleteRoomTemplateHandler",
    "DeleteRosterHandler",
    "GetBootstrapHandler",
    "GetDraftHandler",
    "GetRoomTemplateHandler",
    "GetRosterHandler",
    "ListRoomTemplatesHandler",
    "ListRostersHandler",
    "PatchDraftHandler",
    "UpdateRoomTemplateHandler",
    "UpdateRosterHandler",
]
