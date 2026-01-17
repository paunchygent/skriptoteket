from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from skriptoteket.config import Settings
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CaptureContext:
    capture_id: UUID | None
    capture_success_enabled: bool
    capture_store: LlmCaptureStoreProtocol
    settings: Settings

    async def capture_on_error(self, *, payload: dict[str, object]) -> None:
        if not self.settings.LLM_CAPTURE_ON_ERROR_ENABLED:
            return
        if self.capture_id is None:
            return
        try:
            await self.capture_store.write_capture(
                kind="chat_ops_response",
                capture_id=self.capture_id,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - never break requests for debug capture
            logger.warning(
                "llm_capture_write_failed",
                kind="chat_ops_response",
                capture_id=str(self.capture_id),
                error_type=type(exc).__name__,
            )

    async def capture_on_success(self, *, payload: dict[str, object]) -> None:
        if not self.capture_success_enabled or self.capture_id is None:
            return
        try:
            await self.capture_store.write_capture(
                kind="chat_ops_response",
                capture_id=self.capture_id,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - never break requests for debug capture
            logger.warning(
                "llm_capture_write_failed",
                kind="chat_ops_response",
                capture_id=str(self.capture_id),
                error_type=type(exc).__name__,
            )


def resolve_capture_id(*, raw_correlation_id: object) -> UUID | None:
    if isinstance(raw_correlation_id, str) and raw_correlation_id:
        try:
            return UUID(raw_correlation_id)
        except ValueError:
            return None
    return None


def should_capture_success(*, settings: Settings, capture_id: UUID | None) -> bool:
    if settings.ENVIRONMENT == "production":
        return False
    if not settings.LLM_CAPTURE_ON_SUCCESS_ENABLED:
        return False
    if capture_id is None:
        return False
    return True


def build_capture_context(
    *,
    settings: Settings,
    capture_store: LlmCaptureStoreProtocol,
    capture_id: UUID | None,
) -> CaptureContext:
    return CaptureContext(
        capture_id=capture_id,
        capture_success_enabled=should_capture_success(settings=settings, capture_id=capture_id),
        capture_store=capture_store,
        settings=settings,
    )
