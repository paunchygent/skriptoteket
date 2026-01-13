from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import httpx
import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.prompt_budget import apply_chat_ops_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurnStatus
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.edit_ops_payload_parser import EditOpsPayloadParserProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatMessage,
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProvidersProtocol,
    EditOpsCommand,
    EditOpsHandlerProtocol,
    EditOpsOp,
    EditOpsResult,
    LLMChatRequest,
    PromptEvalMeta,
    VirtualFileId,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

_THREAD_CONTEXT = "editor_chat"
_THREAD_TTL = timedelta(days=30)
_PENDING_TURN_ABANDONED_OUTCOME = "abandoned_by_new_request"
_IN_FLIGHT_MESSAGE = "En chatförfrågan pågår redan. Försök igen om en stund."
_DISABLED_MESSAGE = "AI-redigering är inte tillgänglig just nu. Försök igen senare."
_REMOTE_FALLBACK_REQUIRED_MESSAGE = (
    "Lokala AI-modellen är inte tillgänglig. Tillåt externa API:er (OpenAI) för att fortsätta."
)
_MESSAGE_TOO_LONG = "För långt meddelande: korta ned eller starta en ny chatt."
_GENERATION_ERROR = "Jag kunde inte skapa ett ändringsförslag just nu. Försök igen."
_INVALID_OPS_ERROR = "Jag kunde inte skapa ett giltigt ändringsförslag. Försök igen."

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
    except (ValueError, httpx.ResponseNotRead):
        payload = None
    if payload is not None:
        haystack = str(payload)
    else:
        try:
            haystack = response.text
        except httpx.ResponseNotRead:
            return False
    return "exceed_context_size_error" in haystack.lower()


@dataclass(frozen=True, slots=True)
class _PreparedOpsRequest:
    messages: list[ChatMessage]
    user_payload: str
    tool_session_id: UUID
    turn_id: UUID
    assistant_message_id: UUID
    correlation_id: UUID | None


class EditOpsHandler(EditOpsHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        providers: ChatOpsProvidersProtocol,
        budget_resolver: ChatOpsBudgetResolverProtocol,
        payload_parser: EditOpsPayloadParserProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        capture_store: LlmCaptureStoreProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._budget_resolver = budget_resolver
        self._payload_parser = payload_parser
        self._guard = guard
        self._failover = failover
        self._capture_store = capture_store
        self._uow = uow
        self._sessions = sessions
        self._turns = turns
        self._messages = messages
        self._clock = clock
        self._id_generator = id_generator
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

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
        budget: ChatOpsBudget,
        token_counter: TokenCounterProtocol,
        correlation_id: UUID | None,
    ) -> tuple[_PreparedOpsRequest | None, int]:
        turn_id = self._id_generator.new_uuid()
        user_message_id = self._id_generator.new_uuid()
        assistant_message_id = self._id_generator.new_uuid()

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

            tail_turns = await self._turns.list_tail(
                tool_session_id=session.id,
                limit=max(20, self._settings.LLM_CHAT_TAIL_MAX_MESSAGES),
            )
            if tail_turns and self._is_thread_expired(last_message_at=tail_turns[-1].created_at):
                await self._turns.delete_all(tool_session_id=session.id)
                if session.state:
                    await self._sessions.clear_state(
                        tool_id=command.tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                tail_turns = []

            await self._turns.cancel_pending_turn(
                tool_session_id=session.id,
                failure_outcome=_PENDING_TURN_ABANDONED_OUTCOME,
            )

            completed_turn_ids = [turn.id for turn in tail_turns if turn.status == "complete"]
            existing_rows = await self._messages.list_by_turn_ids(
                tool_session_id=session.id,
                turn_ids=completed_turn_ids,
            )
            existing_messages = [
                ChatMessage(role=row.role, content=row.content) for row in existing_rows
            ]

            _, budgeted_messages, fits = apply_chat_ops_budget(
                system_prompt=system_prompt,
                messages=existing_messages,
                user_payload=user_payload,
                context_window_tokens=budget.context_window_tokens,
                max_output_tokens=budget.max_output_tokens,
                safety_margin_tokens=self._settings.LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS,
                system_prompt_max_tokens=self._settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS,
                token_counter=token_counter,
            )
            prompt_messages_count = len(budgeted_messages) + 1
            if not fits:
                return None, prompt_messages_count

            await self._turns.create_turn(
                turn_id=turn_id,
                tool_session_id=session.id,
                status="pending",
                provider=None,
                correlation_id=correlation_id,
            )
            await self._messages.create_message(
                tool_session_id=session.id,
                turn_id=turn_id,
                message_id=user_message_id,
                role="user",
                content=command.message,
            )
            await self._messages.create_message(
                tool_session_id=session.id,
                turn_id=turn_id,
                message_id=assistant_message_id,
                role="assistant",
                content="",
                meta={"in_reply_to": str(user_message_id)},
            )

        return (
            _PreparedOpsRequest(
                messages=budgeted_messages,
                user_payload=user_payload,
                tool_session_id=session.id,
                turn_id=turn_id,
                assistant_message_id=assistant_message_id,
                correlation_id=correlation_id,
            ),
            prompt_messages_count,
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

        started_at = time.monotonic()
        message_len = len(command.message)
        virtual_files_bytes = sum(
            len(text.encode("utf-8")) for text in command.virtual_files.values()
        )
        raw_correlation_id = get_contextvars().get("correlation_id")
        capture_id: UUID | None = None
        if isinstance(raw_correlation_id, str) and raw_correlation_id:
            try:
                capture_id = UUID(raw_correlation_id)
            except ValueError:
                capture_id = None

        try:
            template_id = self._settings.LLM_CHAT_OPS_TEMPLATE_ID
            base_fingerprints = self._build_base_fingerprints(virtual_files=command.virtual_files)

            def log_result(
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
                elapsed_ms = int((time.monotonic() - started_at) * 1000)
                logger.info(
                    "ai_chat_ops_result",
                    template_id=template_id,
                    user_id=str(actor.id),
                    tool_id=str(command.tool_id),
                    provider=provider,
                    fallback_is_remote=self._providers.fallback_is_remote,
                    allow_remote_fallback=command.allow_remote_fallback,
                    failover_reason=failover_reason,
                    message_len=message_len,
                    virtual_files_bytes=virtual_files_bytes,
                    system_prompt_chars=system_prompt_chars,
                    prompt_messages_count=prompt_messages_count,
                    finish_reason=finish_reason,
                    parse_ok=parse_ok,
                    ops_count=ops_count,
                    outcome=outcome,
                    elapsed_ms=elapsed_ms,
                )

            async def capture_on_error(*, payload: dict[str, object]) -> None:
                if not self._settings.LLM_CAPTURE_ON_ERROR_ENABLED:
                    return
                if capture_id is None:
                    return
                try:
                    await self._capture_store.write_capture(
                        kind="chat_ops_response",
                        capture_id=capture_id,
                        payload=payload,
                    )
                except Exception as exc:  # noqa: BLE001 - never break requests for debug capture
                    logger.warning(
                        "llm_capture_write_failed",
                        kind="chat_ops_response",
                        capture_id=str(capture_id),
                        error_type=type(exc).__name__,
                    )

            if not self._settings.LLM_CHAT_OPS_ENABLED:
                log_result(
                    provider="primary",
                    failover_reason="feature_disabled",
                    system_prompt_chars=0,
                    prompt_messages_count=0,
                    finish_reason=None,
                    parse_ok=False,
                    ops_count=0,
                    outcome="error",
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

            allow_remote_fallback = command.allow_remote_fallback
            decision = await self._failover.decide_route(
                user_id=actor.id,
                tool_id=command.tool_id,
                allow_remote_fallback=allow_remote_fallback,
                fallback_available=self._providers.fallback is not None,
                fallback_is_remote=self._providers.fallback_is_remote,
            )
            if decision.blocked == "remote_fallback_required":
                log_result(
                    provider=decision.provider,
                    failover_reason=decision.reason,
                    system_prompt_chars=0,
                    prompt_messages_count=0,
                    finish_reason=None,
                    parse_ok=False,
                    ops_count=0,
                    outcome="error",
                )
                return EditOpsResult(
                    enabled=False,
                    assistant_message=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=0,
                    ),
                )

            if decision.provider == "fallback":
                model_for_counting = (
                    self._settings.LLM_CHAT_OPS_FALLBACK_MODEL.strip()
                    or self._settings.LLM_CHAT_OPS_MODEL
                )
            else:
                model_for_counting = self._settings.LLM_CHAT_OPS_MODEL
            token_counter = self._token_counters.for_model(model=model_for_counting)

            try:
                if self._system_prompt_loader is not None:
                    system_prompt = self._system_prompt_loader(template_id)
                else:
                    system_prompt = compose_system_prompt(
                        template_id=template_id,
                        settings=self._settings,
                        token_counter=token_counter,
                    ).text
            except (OSError, PromptTemplateError) as exc:
                logger.warning(
                    "ai_chat_ops_system_prompt_unavailable",
                    template_id=template_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    model=model_for_counting,
                    system_prompt_max_tokens=self._settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS,
                )
                log_result(
                    provider=decision.provider,
                    failover_reason=decision.reason,
                    system_prompt_chars=0,
                    prompt_messages_count=0,
                    finish_reason=None,
                    parse_ok=False,
                    ops_count=0,
                    outcome="error",
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
            budget = self._budget_resolver.resolve_chat_ops_budget(provider=decision.provider)

            prepared, prompt_messages_count = await self._prepare_request(
                actor=actor,
                command=command,
                system_prompt=system_prompt,
                user_payload=user_payload,
                budget=budget,
                token_counter=token_counter,
                correlation_id=capture_id,
            )
            if prepared is None:
                log_result(
                    provider=decision.provider,
                    failover_reason=decision.reason,
                    system_prompt_chars=len(system_prompt),
                    prompt_messages_count=prompt_messages_count,
                    finish_reason=None,
                    parse_ok=False,
                    ops_count=0,
                    outcome="over_budget",
                )
                await capture_on_error(
                    payload={
                        "outcome": "over_budget",
                        "stage": "preflight_budget",
                        "template_id": template_id,
                        "user_id": str(actor.id),
                        "tool_id": str(command.tool_id),
                        "provider": decision.provider,
                        "failover_reason": decision.reason,
                        "fallback_is_remote": self._providers.fallback_is_remote,
                        "allow_remote_fallback": command.allow_remote_fallback,
                        "message_len": message_len,
                        "virtual_files_bytes": virtual_files_bytes,
                        "system_prompt_chars": len(system_prompt),
                        "prompt_messages_count": prompt_messages_count,
                        "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                    }
                )
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
                message_len=message_len,
                virtual_files_bytes=virtual_files_bytes,
            )

            assistant_message = _GENERATION_ERROR
            ops: list[EditOpsOp] = []
            eval_outcome = "error"
            log_outcome = "error"
            finish_reason: str | None = None
            parse_ok = False
            provider_key = decision.provider
            failover_reason: str | None = decision.reason
            upstream_error: dict[str, object] | None = None

            async def complete(provider_key: str):
                provider = (
                    self._providers.primary
                    if provider_key == "primary"
                    else self._providers.fallback
                )
                if provider is None:
                    raise ValueError("Fallback provider is not configured")

                await self._failover.acquire_inflight(provider=provider_key)  # type: ignore[arg-type]
                try:
                    return await provider.complete_chat_ops(
                        request=request,
                        system_prompt=system_prompt,
                    )
                finally:
                    await self._failover.release_inflight(provider=provider_key)  # type: ignore[arg-type]

            def is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
                if exc.response is None:
                    return False
                status = exc.response.status_code
                return status == 429 or status >= 500

            if provider_key == "fallback":
                await self._failover.mark_fallback_used(user_id=actor.id, tool_id=command.tool_id)

            response = None
            first_error: Exception | None = None
            try:
                response = await complete(provider_key)
            except httpx.TimeoutException as exc:
                first_error = exc
                eval_outcome = "timeout"
                log_outcome = "timeout"
                await self._failover.record_failure(provider=provider_key)
            except httpx.HTTPStatusError as exc:
                first_error = exc
                eval_outcome = "over_budget" if _is_context_window_error(exc) else "error"
                log_outcome = eval_outcome
                upstream_error = {
                    "error_type": type(exc).__name__,
                    "status_code": exc.response.status_code if exc.response is not None else None,
                }
                if exc.response is not None:
                    try:
                        upstream_error["payload"] = exc.response.json()
                    except ValueError:
                        upstream_error["payload"] = exc.response.text[:2000]
                if is_retryable_status(exc):
                    await self._failover.record_failure(provider=provider_key)
            except (httpx.RequestError, ValueError) as exc:
                first_error = exc
                eval_outcome = "error"
                log_outcome = "error"
                upstream_error = {
                    "error_type": type(exc).__name__,
                }
                await self._failover.record_failure(provider=provider_key)
            else:
                await self._failover.record_success(provider=provider_key)

            can_use_fallback = self._providers.fallback is not None and (
                allow_remote_fallback or not self._providers.fallback_is_remote
            )
            retryable_primary_failure = (
                response is None
                and provider_key == "primary"
                and (
                    isinstance(
                        first_error, (httpx.TimeoutException, httpx.RequestError, ValueError)
                    )
                    or (
                        isinstance(first_error, httpx.HTTPStatusError)
                        and is_retryable_status(first_error)
                    )
                )
            )
            if (
                retryable_primary_failure
                and self._providers.fallback is not None
                and self._providers.fallback_is_remote
                and not allow_remote_fallback
            ):
                async with self._uow:
                    await self._messages.update_message_content_if_pending_turn(
                        tool_session_id=prepared.tool_session_id,
                        turn_id=prepared.turn_id,
                        message_id=prepared.assistant_message_id,
                        content=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                        correlation_id=prepared.correlation_id,
                    )
                    await self._turns.update_status(
                        turn_id=prepared.turn_id,
                        status="failed",
                        correlation_id=prepared.correlation_id,
                        failure_outcome="remote_fallback_required",
                        provider=provider_key,
                    )
                log_result(
                    provider="fallback",
                    failover_reason="retryable_primary_failure",
                    system_prompt_chars=len(system_prompt),
                    prompt_messages_count=prompt_messages_count,
                    finish_reason=None,
                    parse_ok=False,
                    ops_count=0,
                    outcome="error",
                )
                return EditOpsResult(
                    enabled=False,
                    assistant_message=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=len(system_prompt),
                    ),
                )
            should_failover = retryable_primary_failure and can_use_fallback
            if should_failover:
                provider_key = "fallback"
                failover_reason = "retryable_primary_failure"
                await self._failover.mark_fallback_used(user_id=actor.id, tool_id=command.tool_id)
                try:
                    response = await complete(provider_key)
                except httpx.TimeoutException:
                    eval_outcome = "timeout"
                    log_outcome = "timeout"
                    upstream_error = {"error_type": "TimeoutException"}
                    await self._failover.record_failure(provider=provider_key)
                except httpx.HTTPStatusError as exc:
                    eval_outcome = "over_budget" if _is_context_window_error(exc) else "error"
                    log_outcome = eval_outcome
                    upstream_error = {
                        "error_type": type(exc).__name__,
                        "status_code": exc.response.status_code
                        if exc.response is not None
                        else None,
                    }
                    if exc.response is not None:
                        try:
                            upstream_error["payload"] = exc.response.json()
                        except ValueError:
                            upstream_error["payload"] = exc.response.text[:2000]
                    if is_retryable_status(exc):
                        await self._failover.record_failure(provider=provider_key)
                except (httpx.RequestError, ValueError):
                    eval_outcome = "error"
                    log_outcome = "error"
                    upstream_error = {"error_type": "RequestError"}
                    await self._failover.record_failure(provider=provider_key)
                else:
                    await self._failover.record_success(provider=provider_key)

            if response is not None:
                finish_reason = response.finish_reason
                if response.finish_reason == "length":
                    eval_outcome = "truncated"
                    log_outcome = "truncated"
                else:
                    parsed = self._payload_parser.parse(raw=response.content)
                    parse_ok = parsed is not None
                    if parsed is None:
                        assistant_message = _INVALID_OPS_ERROR
                        eval_outcome = "error"
                        log_outcome = "parse_failed"
                    elif self._ops_compatible_with_request(command=command, ops=parsed.ops):
                        ops = parsed.ops
                        assistant_message = parsed.assistant_message.strip() or assistant_message
                        eval_outcome = "ok" if ops else "empty"
                        log_outcome = eval_outcome
            else:
                ops = []
                assistant_message = _INVALID_OPS_ERROR
                eval_outcome = "error"
                log_outcome = "invalid_ops"

            turn_status: ToolSessionTurnStatus = (
                "complete" if log_outcome in {"ok", "empty"} else "failed"
            )
            failure_outcome = None if turn_status == "complete" else log_outcome
            async with self._uow:
                await self._messages.update_message_content_if_pending_turn(
                    tool_session_id=prepared.tool_session_id,
                    turn_id=prepared.turn_id,
                    message_id=prepared.assistant_message_id,
                    content=assistant_message,
                    correlation_id=prepared.correlation_id,
                )
                await self._turns.update_status(
                    turn_id=prepared.turn_id,
                    status=turn_status,
                    correlation_id=prepared.correlation_id,
                    failure_outcome=failure_outcome,
                    provider=provider_key,
                )

            if log_outcome not in {"ok", "empty"}:
                await capture_on_error(
                    payload={
                        "outcome": log_outcome,
                        "template_id": template_id,
                        "user_id": str(actor.id),
                        "tool_id": str(command.tool_id),
                        "provider": provider_key,
                        "failover_reason": failover_reason,
                        "fallback_is_remote": self._providers.fallback_is_remote,
                        "allow_remote_fallback": command.allow_remote_fallback,
                        "message_len": message_len,
                        "virtual_files_bytes": virtual_files_bytes,
                        "system_prompt_chars": len(system_prompt),
                        "prompt_messages_count": prompt_messages_count,
                        "finish_reason": finish_reason,
                        "parse_ok": parse_ok,
                        "ops_count": len(ops),
                        "upstream_error": upstream_error,
                        "raw_payload": response.raw_payload if response is not None else None,
                        "extracted_content": response.content if response is not None else None,
                        "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                    }
                )

            log_result(
                provider=provider_key,
                failover_reason=failover_reason,
                system_prompt_chars=len(system_prompt),
                prompt_messages_count=prompt_messages_count,
                finish_reason=finish_reason,
                parse_ok=parse_ok,
                ops_count=len(ops),
                outcome=log_outcome,
            )

            return EditOpsResult(
                enabled=True,
                assistant_message=assistant_message,
                ops=ops,
                base_fingerprints=base_fingerprints,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome=eval_outcome,
                    system_prompt_chars=len(system_prompt),
                ),
            )
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
