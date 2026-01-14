from __future__ import annotations

from datetime import timedelta

from skriptoteket.protocols.llm import VirtualFileId

DISABLED_MESSAGE = "Kodassistenten är inte tillgänglig just nu. Försök igen senare."
REMOTE_FALLBACK_REQUIRED_MESSAGE = (
    "Den lokala AI-modellen är inte tillgänglig. "
    "Aktivera externa AI-API:er (OpenAI) för att fortsätta."
)
REMOTE_FALLBACK_REQUIRED_CODE = "remote_fallback_required"
MESSAGE_TOO_LONG = "För långt meddelande: korta ned eller starta en ny chatt."
IN_FLIGHT_MESSAGE = "En chatförfrågan pågår redan. Försök igen om en stund."

THREAD_CONTEXT = "editor_chat"
THREAD_TTL = timedelta(days=30)
PENDING_TURN_ABANDONED_OUTCOME = "abandoned_by_new_request"
BASE_VERSION_KEY = "base_version_id"

VIRTUAL_FILE_IDS: tuple[VirtualFileId, ...] = (
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
)
CHAT_USER_PAYLOAD_KIND = "editor_chat_user_payload"
CHAT_USER_PAYLOAD_SCHEMA_VERSION = 1

STREAM_FLUSH_MIN_CHARS = 256
STREAM_FLUSH_MAX_INTERVAL_SECONDS = 0.75
