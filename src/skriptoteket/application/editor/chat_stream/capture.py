"""Chat stream capture helpers."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

import structlog

from skriptoteket.application.editor.chat_shared import VIRTUAL_FILE_IDS
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import EditorChatCommand, LLMChatRequest
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol

logger = structlog.get_logger(__name__)


def _fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ordered_virtual_file_ids(virtual_files: dict[str, str]) -> list[str]:
    ordered = [file_id for file_id in VIRTUAL_FILE_IDS if file_id in virtual_files]
    extras = sorted(set(virtual_files) - set(ordered))
    return ordered + extras


def _build_base_hashes(virtual_files: dict[str, str]) -> dict[str, str]:
    return {
        file_id: _fingerprint(f"{file_id}\u0000{virtual_files[file_id]}")
        for file_id in _ordered_virtual_file_ids(virtual_files)
    }


def _build_base_hash(virtual_files: dict[str, str]) -> str:
    payload = "\u0000".join(
        [
            f"{file_id}\u0000{virtual_files[file_id]}"
            for file_id in _ordered_virtual_file_ids(virtual_files)
        ]
    )
    return _fingerprint(payload)


def _extract_virtual_files_from_request(
    request: LLMChatRequest,
) -> tuple[dict[str, str] | None, list[str] | None, str]:
    if not request.messages:
        return None, None, "none"
    last = request.messages[-1]
    if last.role != "user":
        return None, None, "none"
    try:
        payload = json.loads(last.content)
    except (ValueError, TypeError):
        return None, None, "none"
    if not isinstance(payload, dict):
        return None, None, "none"
    virtual_files = payload.get("virtual_files")
    if not isinstance(virtual_files, dict):
        return None, None, "none"
    normalized: dict[str, str] = {}
    for key, value in virtual_files.items():
        if isinstance(value, str):
            normalized[str(key)] = value
        else:
            normalized[str(key)] = json.dumps(value, ensure_ascii=False)
    omitted = payload.get("omitted_virtual_file_ids")
    omitted_ids = omitted if isinstance(omitted, list) else None
    return normalized, omitted_ids, "payload"


def _should_capture_context(*, settings: Settings, capture_id: object | None) -> bool:
    if settings.ENVIRONMENT == "production":
        return False
    if not settings.LLM_CAPTURE_ON_SUCCESS_ENABLED:
        return False
    if capture_id is None:
        return False
    return True


async def capture_chat_request_context(
    *,
    settings: Settings,
    capture_store: LlmCaptureStoreProtocol,
    template_id: str,
    actor: User,
    command: EditorChatCommand,
    request: LLMChatRequest,
    capture_id: UUID | None,
) -> None:
    if not _should_capture_context(settings=settings, capture_id=capture_id):
        return
    assert capture_id is not None
    virtual_files, omitted_ids, source = _extract_virtual_files_from_request(request)
    if virtual_files is None and command.virtual_files is not None:
        virtual_files = {str(key): value for key, value in command.virtual_files.items()}
        source = "command"
    payload: dict[str, object] = {
        "template_id": template_id,
        "user_id": str(actor.id),
        "tool_id": str(command.tool_id),
        "active_file": command.active_file,
        "virtual_files_source": source,
        "omitted_virtual_file_ids": omitted_ids,
    }
    if virtual_files is not None:
        payload["virtual_files_bytes"] = sum(
            len(text.encode("utf-8")) for text in virtual_files.values()
        )
        payload["base_hashes"] = _build_base_hashes(virtual_files)
        payload["base_hash"] = _build_base_hash(virtual_files)
    try:
        await capture_store.write_capture(
            kind="chat_request_context",
            capture_id=capture_id,
            payload=payload,
        )
    except Exception as exc:  # noqa: BLE001 - never break chat for debug capture
        logger.warning(
            "llm_capture_write_failed",
            kind="chat_request_context",
            capture_id=str(capture_id),
            error_type=type(exc).__name__,
        )
