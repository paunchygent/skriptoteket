from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from skriptoteket.application.editor.prompt_budget import apply_chat_ops_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatInFlightGuardProtocol,
    ChatMessage,
    ChatOpsProviderProtocol,
    EditOpsCommand,
    EditOpsHandlerProtocol,
    EditOpsOp,
    EditOpsResult,
    LLMChatRequest,
    PromptEvalMeta,
    VirtualFileId,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

_THREAD_CONTEXT = "editor_chat"
_THREAD_TTL = timedelta(days=30)
_IN_FLIGHT_MESSAGE = "En chatförfrågan pågår redan. Försök igen om en stund."
_DISABLED_MESSAGE = "AI-redigering är inte tillgänglig just nu. Försök igen senare."
_MESSAGE_TOO_LONG = "För långt meddelande: korta ned eller starta en ny chatt."
_GENERATION_ERROR = "Jag kunde inte skapa ett ändringsförslag just nu. Försök igen."
_INVALID_OPS_ERROR = "Jag kunde inte skapa ett giltigt ändringsförslag. Försök igen."

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
_VIRTUAL_FILE_IDS: tuple[VirtualFileId, ...] = (
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
)


def _is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        payload = None
    haystack = str(payload) if payload is not None else response.text
    return "exceed_context_size_error" in haystack.lower()


def _extract_first_fenced_block(text: str) -> str | None:
    match = _CODE_FENCE_PATTERN.search(text)
    if not match:
        return None
    return match.group(1)


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


class _EditOpsPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assistant_message: str
    ops: list[EditOpsOp]


@dataclass(frozen=True, slots=True)
class _PreparedOpsRequest:
    messages: list[ChatMessage]
    user_payload: str
    user_message_id: UUID
    tool_session_id: UUID


class EditOpsHandler(EditOpsHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        provider: ChatOpsProviderProtocol,
        guard: ChatInFlightGuardProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._guard = guard
        self._uow = uow
        self._sessions = sessions
        self._messages = messages
        self._clock = clock
        self._id_generator = id_generator
        self._system_prompt_loader = system_prompt_loader or (
            lambda template_id: compose_system_prompt(
                template_id=template_id,
                settings=settings,
            ).text
        )

    def _is_thread_expired(self, *, last_message_at: datetime) -> bool:
        return self._clock.now() - last_message_at > _THREAD_TTL

    def _fingerprint(self, text: str) -> str:
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _build_base_fingerprints(
        self, *, virtual_files: dict[VirtualFileId, str]
    ) -> dict[VirtualFileId, str]:
        return {file_id: self._fingerprint(virtual_files[file_id]) for file_id in _VIRTUAL_FILE_IDS}

    def _build_user_payload(self, *, command: EditOpsCommand) -> str:
        virtual_files = {file_id: command.virtual_files[file_id] for file_id in _VIRTUAL_FILE_IDS}
        payload: dict[str, object] = {
            "message": command.message,
            "active_file": command.active_file,
            "virtual_files": virtual_files,
        }
        if command.selection is not None:
            payload["selection"] = {"from": command.selection.start, "to": command.selection.end}
        if command.cursor is not None:
            payload["cursor"] = {"pos": command.cursor.pos}
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _parse_payload(self, raw: str) -> _EditOpsPayload | None:
        candidates = [raw.strip()]
        fenced = _extract_first_fenced_block(raw)
        if fenced:
            candidates.append(fenced.strip())
        extracted = _extract_json_object(raw)
        if extracted:
            candidates.append(extracted.strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            try:
                return _EditOpsPayload.model_validate(payload)
            except ValidationError:
                continue
        return None

    def _ops_compatible_with_request(
        self, *, command: EditOpsCommand, ops: list[EditOpsOp]
    ) -> bool:
        for op in ops:
            if hasattr(op, "target") and op.target.kind in {"cursor", "selection"}:
                if op.target_file != command.active_file:
                    return False

            if hasattr(op, "target") and op.target.kind == "cursor":
                if command.cursor is None:
                    return False

            if hasattr(op, "target") and op.target.kind == "selection":
                if command.selection is None:
                    return False

        return True

    async def _prepare_request(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
        system_prompt: str,
        user_payload: str,
    ) -> _PreparedOpsRequest | None:
        async with self._uow:
            session = await self._sessions.get(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=_THREAD_CONTEXT,
            )
            if session is None:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=_THREAD_CONTEXT,
                )

            tail = await self._messages.list_tail(
                tool_session_id=session.id,
                limit=self._settings.LLM_CHAT_TAIL_MAX_MESSAGES,
            )
            if tail and self._is_thread_expired(last_message_at=tail[-1].created_at):
                await self._messages.delete_all(tool_session_id=session.id)
                if session.state:
                    await self._sessions.clear_state(
                        tool_id=command.tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                tail = []

            existing_messages = [
                ChatMessage(role=message.role, content=message.content) for message in tail
            ]

            _, budgeted_messages, fits = apply_chat_ops_budget(
                system_prompt=system_prompt,
                messages=existing_messages,
                user_payload=user_payload,
                context_window_tokens=self._settings.LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self._settings.LLM_CHAT_OPS_MAX_TOKENS,
                safety_margin_tokens=self._settings.LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS,
                system_prompt_max_tokens=self._settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS,
            )
            if not fits:
                return None

            user_message_id = self._id_generator.new_uuid()
            await self._messages.append_message(
                tool_session_id=session.id,
                message_id=user_message_id,
                role="user",
                content=command.message,
            )

        return _PreparedOpsRequest(
            messages=budgeted_messages,
            user_payload=user_payload,
            user_message_id=user_message_id,
            tool_session_id=session.id,
        )

    async def _persist_assistant_message(
        self,
        *,
        tool_session_id: UUID,
        assistant_message: str,
    ) -> None:
        async with self._uow:
            await self._messages.append_message(
                tool_session_id=tool_session_id,
                message_id=self._id_generator.new_uuid(),
                role="assistant",
                content=assistant_message,
            )

    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
    ) -> EditOpsResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        guard_acquired = await self._guard.try_acquire(user_id=actor.id, tool_id=command.tool_id)
        if not guard_acquired:
            raise DomainError(code=ErrorCode.CONFLICT, message=_IN_FLIGHT_MESSAGE)

        try:
            template_id = self._settings.LLM_CHAT_OPS_TEMPLATE_ID
            base_fingerprints = self._build_base_fingerprints(virtual_files=command.virtual_files)

            if not self._settings.LLM_CHAT_OPS_ENABLED:
                return EditOpsResult(
                    enabled=False,
                    assistant_message=_DISABLED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=0,
                    ),
                )

            try:
                system_prompt = self._system_prompt_loader(template_id)
            except (OSError, PromptTemplateError):
                logger.warning(
                    "ai_chat_ops_system_prompt_unavailable",
                    template_id=template_id,
                )
                return EditOpsResult(
                    enabled=False,
                    assistant_message=_DISABLED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=0,
                    ),
                )

            user_payload = self._build_user_payload(command=command)

            prepared = await self._prepare_request(
                actor=actor,
                command=command,
                system_prompt=system_prompt,
                user_payload=user_payload,
            )
            if prepared is None:
                return EditOpsResult(
                    enabled=True,
                    assistant_message=_MESSAGE_TOO_LONG,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="over_budget",
                        system_prompt_chars=len(system_prompt),
                    ),
                )

            prompt_messages = [
                *prepared.messages,
                ChatMessage(role="user", content=prepared.user_payload),
            ]
            request = LLMChatRequest(messages=prompt_messages)

            logger.info(
                "ai_chat_ops_request",
                template_id=template_id,
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
                message_len=len(command.message),
                virtual_files_bytes=sum(len(text) for text in command.virtual_files.values()),
            )

            assistant_message = _GENERATION_ERROR
            ops: list[EditOpsOp] = []
            outcome = "error"

            try:
                response = await self._provider.complete_chat_ops(
                    request=request,
                    system_prompt=system_prompt,
                )
            except httpx.TimeoutException:
                outcome = "timeout"
            except httpx.HTTPStatusError as exc:
                if _is_context_window_error(exc):
                    outcome = "over_budget"
                else:
                    outcome = "error"
            except (httpx.RequestError, ValueError):
                outcome = "error"
            else:
                if response.finish_reason == "length":
                    outcome = "truncated"
                else:
                    parsed = self._parse_payload(response.content)
                    if parsed is not None:
                        if self._ops_compatible_with_request(command=command, ops=parsed.ops):
                            ops = parsed.ops
                            assistant_message = (
                                parsed.assistant_message.strip() or assistant_message
                            )
                            outcome = "ok" if ops else "empty"
                        else:
                            ops = []
                            assistant_message = _INVALID_OPS_ERROR
                            outcome = "error"

            await self._persist_assistant_message(
                tool_session_id=prepared.tool_session_id,
                assistant_message=assistant_message,
            )

            return EditOpsResult(
                enabled=True,
                assistant_message=assistant_message,
                ops=ops,
                base_fingerprints=base_fingerprints,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome=outcome,
                    system_prompt_chars=len(system_prompt),
                ),
            )
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
