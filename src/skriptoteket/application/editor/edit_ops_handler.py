from __future__ import annotations

import time
from collections.abc import Callable

import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.prompt_composer import PromptTemplateError
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.edit_ops_payload_parser import EditOpsPayloadParserProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatMessage,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProvidersProtocol,
    EditOpsCommand,
    EditOpsHandlerProtocol,
    EditOpsResult,
    LLMChatRequest,
    PromptEvalMeta,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .edit_ops.budgeting import (
    build_base_fingerprints,
    build_base_hash,
    build_base_hashes,
    build_user_payload,
)
from .edit_ops.capture import build_capture_context, resolve_capture_id
from .edit_ops.constants import (
    DISABLED_MESSAGE,
    IN_FLIGHT_MESSAGE,
    REMOTE_FALLBACK_REQUIRED_MESSAGE,
)
from .edit_ops.execution import execute_chat_ops
from .edit_ops.logging import EditOpsLogContext
from .edit_ops.over_budget import handle_over_budget
from .edit_ops.persistence import complete_turn, update_turn_failure_with_message
from .edit_ops.preflight_orchestrator import prepare_preflight_context
from .edit_ops.routing import resolve_model_for_counting

logger = structlog.get_logger(__name__)


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

    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
    ) -> EditOpsResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        guard_acquired = await self._guard.try_acquire(user_id=actor.id, tool_id=command.tool_id)
        if not guard_acquired:
            raise DomainError(code=ErrorCode.CONFLICT, message=IN_FLIGHT_MESSAGE)

        started_at = time.monotonic()
        message_len = len(command.message)
        virtual_files_bytes = sum(
            len(text.encode("utf-8")) for text in command.virtual_files.values()
        )
        capture_id = resolve_capture_id(raw_correlation_id=get_contextvars().get("correlation_id"))
        capture_context = build_capture_context(
            settings=self._settings,
            capture_store=self._capture_store,
            capture_id=capture_id,
        )

        try:
            template_id = self._settings.LLM_CHAT_OPS_TEMPLATE_ID
            base_fingerprints = build_base_fingerprints(virtual_files=command.virtual_files)
            base_hashes = build_base_hashes(virtual_files=command.virtual_files)
            base_hash = build_base_hash(virtual_files=command.virtual_files)
            log_context = EditOpsLogContext(
                template_id=template_id,
                user_id=actor.id,
                tool_id=command.tool_id,
                fallback_is_remote=self._providers.fallback_is_remote,
                allow_remote_fallback=command.allow_remote_fallback,
                message_len=message_len,
                virtual_files_bytes=virtual_files_bytes,
                started_at=started_at,
            )

            if not self._settings.LLM_CHAT_OPS_ENABLED:
                log_context.log_result(
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
                    assistant_message=DISABLED_MESSAGE,
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
                log_context.log_result(
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
                    assistant_message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=0,
                    ),
                )

            model_for_counting = resolve_model_for_counting(
                settings=self._settings,
                decision=decision,
            )
            user_payload = build_user_payload(command=command)
            try:
                preflight_context = await prepare_preflight_context(
                    settings=self._settings,
                    providers=self._providers,
                    budget_resolver=self._budget_resolver,
                    token_counters=self._token_counters,
                    failover=self._failover,
                    uow=self._uow,
                    sessions=self._sessions,
                    turns=self._turns,
                    messages=self._messages,
                    clock=self._clock,
                    id_generator=self._id_generator,
                    command=command,
                    actor_id=actor.id,
                    decision=decision,
                    template_id=template_id,
                    system_prompt_loader=self._system_prompt_loader,
                    user_payload=user_payload,
                    capture_id=capture_id,
                    allow_remote_fallback=allow_remote_fallback,
                    message_len=message_len,
                    virtual_files_bytes=virtual_files_bytes,
                )
            except (OSError, PromptTemplateError) as exc:
                logger.warning(
                    "ai_chat_ops_system_prompt_unavailable",
                    template_id=template_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    model=self._settings.LLM_CHAT_OPS_MODEL,
                    system_prompt_max_tokens=self._settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS,
                )
                log_context.log_result(
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
                    assistant_message=DISABLED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=0,
                    ),
                )

            decision = preflight_context.decision
            prepared = preflight_context.prepared
            prompt_messages_count = preflight_context.prompt_messages_count
            system_prompt = preflight_context.system_prompt
            budget = preflight_context.budget
            token_counter = preflight_context.token_counter
            model_for_counting = preflight_context.model_for_counting

            if prepared is None:
                return await handle_over_budget(
                    settings=self._settings,
                    actor=actor,
                    command=command,
                    decision=decision,
                    model_for_counting=model_for_counting,
                    system_prompt=system_prompt,
                    user_payload=user_payload,
                    budget=budget,
                    token_counter=token_counter,
                    prompt_messages_count=prompt_messages_count,
                    base_hash=base_hash,
                    base_hashes=base_hashes,
                    base_fingerprints=base_fingerprints,
                    log_context=log_context,
                    capture_context=capture_context,
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

            execution = await execute_chat_ops(
                providers=self._providers,
                failover=self._failover,
                payload_parser=self._payload_parser,
                command=command,
                request=request,
                system_prompt=system_prompt,
                decision=decision,
                allow_remote_fallback=allow_remote_fallback,
                user_id=actor.id,
            )

            if execution.requires_remote_fallback:
                await update_turn_failure_with_message(
                    uow=self._uow,
                    messages=self._messages,
                    turns=self._turns,
                    tool_session_id=prepared.tool_session_id,
                    turn_id=prepared.turn_id,
                    assistant_message_id=prepared.assistant_message_id,
                    assistant_message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    provider=execution.provider_key,
                    failure_outcome="remote_fallback_required",
                    correlation_id=prepared.correlation_id,
                )
                log_context.log_result(
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
                    assistant_message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    ops=[],
                    base_fingerprints=base_fingerprints,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="error",
                        system_prompt_chars=len(system_prompt),
                    ),
                )

            await complete_turn(
                uow=self._uow,
                messages=self._messages,
                turns=self._turns,
                tool_session_id=prepared.tool_session_id,
                turn_id=prepared.turn_id,
                assistant_message_id=prepared.assistant_message_id,
                assistant_message=execution.assistant_message,
                provider=execution.provider_key,
                outcome=execution.log_outcome,
                correlation_id=prepared.correlation_id,
            )

            if execution.log_outcome not in {"ok", "empty"}:
                await capture_context.capture_on_error(
                    payload={
                        "outcome": execution.log_outcome,
                        "template_id": template_id,
                        "user_id": str(actor.id),
                        "tool_id": str(command.tool_id),
                        "provider": execution.provider_key,
                        "failover_reason": execution.failover_reason,
                        "fallback_is_remote": self._providers.fallback_is_remote,
                        "allow_remote_fallback": command.allow_remote_fallback,
                        "message_len": message_len,
                        "virtual_files_bytes": virtual_files_bytes,
                        "base_hash": base_hash,
                        "base_hashes": base_hashes,
                        "base_fingerprints": base_fingerprints,
                        "system_prompt_chars": len(system_prompt),
                        "prompt_messages_count": prompt_messages_count,
                        "finish_reason": execution.finish_reason,
                        "parse_ok": execution.parse_ok,
                        "ops_count": len(execution.ops),
                        "upstream_error": execution.upstream_error,
                        "raw_payload": execution.raw_payload,
                        "extracted_content": execution.extracted_content,
                        "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                    }
                )
            elif capture_context.capture_success_enabled:
                await capture_context.capture_on_success(
                    payload={
                        "outcome": execution.log_outcome,
                        "template_id": template_id,
                        "user_id": str(actor.id),
                        "tool_id": str(command.tool_id),
                        "provider": execution.provider_key,
                        "failover_reason": execution.failover_reason,
                        "fallback_is_remote": self._providers.fallback_is_remote,
                        "allow_remote_fallback": command.allow_remote_fallback,
                        "message_len": message_len,
                        "virtual_files_bytes": virtual_files_bytes,
                        "base_hash": base_hash,
                        "base_hashes": base_hashes,
                        "base_fingerprints": base_fingerprints,
                        "system_prompt_chars": len(system_prompt),
                        "prompt_messages_count": prompt_messages_count,
                        "finish_reason": execution.finish_reason,
                        "parse_ok": execution.parse_ok,
                        "ops_count": len(execution.ops),
                        "raw_payload": execution.raw_payload,
                        "extracted_content": execution.extracted_content,
                        "assistant_message": execution.assistant_message,
                        "ops": [op.model_dump(exclude_none=True) for op in execution.ops],
                        "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                    }
                )

            log_context.log_result(
                provider=execution.provider_key,
                failover_reason=execution.failover_reason,
                system_prompt_chars=len(system_prompt),
                prompt_messages_count=prompt_messages_count,
                finish_reason=execution.finish_reason,
                parse_ok=execution.parse_ok,
                ops_count=len(execution.ops),
                outcome=execution.log_outcome,
            )

            return EditOpsResult(
                enabled=True,
                assistant_message=execution.assistant_message,
                ops=execution.ops,
                base_fingerprints=base_fingerprints,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome=execution.eval_outcome,
                    system_prompt_chars=len(system_prompt),
                ),
            )
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
