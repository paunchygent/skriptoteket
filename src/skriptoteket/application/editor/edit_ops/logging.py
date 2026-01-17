from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class EditOpsLogContext:
    template_id: str
    user_id: UUID
    tool_id: UUID
    fallback_is_remote: bool
    allow_remote_fallback: bool
    message_len: int
    virtual_files_bytes: int
    started_at: float

    def log_result(
        self,
        *,
        provider: str,
        failover_reason: str | None,
        system_prompt_chars: int,
        prompt_messages_count: int,
        finish_reason: str | None,
        parse_ok: bool,
        ops_count: int,
        outcome: str,
    ) -> None:
        elapsed_ms = int((time.monotonic() - self.started_at) * 1000)
        logger.info(
            "ai_chat_ops_result",
            template_id=self.template_id,
            user_id=str(self.user_id),
            tool_id=str(self.tool_id),
            provider=provider,
            fallback_is_remote=self.fallback_is_remote,
            allow_remote_fallback=self.allow_remote_fallback,
            failover_reason=failover_reason,
            message_len=self.message_len,
            virtual_files_bytes=self.virtual_files_bytes,
            system_prompt_chars=system_prompt_chars,
            prompt_messages_count=prompt_messages_count,
            finish_reason=finish_reason,
            parse_ok=parse_ok,
            ops_count=ops_count,
            outcome=outcome,
            elapsed_ms=elapsed_ms,
        )
