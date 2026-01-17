from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Protocol
from uuid import UUID

LlmCaptureKind = Literal[
    "chat_ops_response",
    "edit_ops_preview_failure",
    "chat_request_context",
]


class LlmCaptureStoreProtocol(Protocol):
    async def write_capture(
        self,
        *,
        kind: LlmCaptureKind,
        capture_id: UUID,
        payload: Mapping[str, object],
    ) -> None:
        """Persist a sensitive debug capture for platform developers.

        This must never raise; callers should not fail requests because capture storage is
        unavailable.
        """
