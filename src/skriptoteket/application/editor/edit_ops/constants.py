from __future__ import annotations

from datetime import timedelta

from skriptoteket.protocols.llm import VirtualFileId

THREAD_CONTEXT = "editor_chat"
THREAD_TTL = timedelta(days=30)
PENDING_TURN_ABANDONED_OUTCOME = "abandoned_by_new_request"
TURN_PROVIDER = "door"
AI_LIMIT_FAILURE_OUTCOME = "ai_daily_limit_reached"
AI_DOOR_BUSY_FAILURE_OUTCOME = "ai_door_busy"

IN_FLIGHT_MESSAGE = "En chatförfrågan pågår redan. Försök igen om en stund."
DISABLED_MESSAGE = "AI-redigering är inte tillgänglig just nu. Försök igen senare."
MESSAGE_TOO_LONG = "För långt meddelande: korta ned eller starta en ny chatt."
GENERATION_ERROR = "Jag kunde inte skapa ett ändringsförslag just nu. Försök igen."
INVALID_OPS_ERROR = "Jag kunde inte skapa ett giltigt ändringsförslag. Försök igen."
PATCH_ONLY_REQUIRED_ERROR = (
    "Jag kunde inte skapa ett giltigt ändringsförslag. "
    "Förslaget måste vara en patch (unified diff) per fil. Regenerera och försök igen."
)

VIRTUAL_FILE_IDS: tuple[VirtualFileId, ...] = (
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
)
