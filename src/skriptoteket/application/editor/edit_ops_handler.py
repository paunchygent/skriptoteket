from __future__ import annotations

from collections.abc import Callable

from skriptoteket.application.editor.edit_ops.flow import EditOpsFlow
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
    ChatOpsBudgetResolverProtocol,
    ChatOpsProvidersProtocol,
    EditOpsCommand,
    EditOpsHandlerProtocol,
    EditOpsResult,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .edit_ops.constants import IN_FLIGHT_MESSAGE


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
        self._guard = guard
        self._flow = EditOpsFlow(
            settings=settings,
            providers=providers,
            budget_resolver=budget_resolver,
            payload_parser=payload_parser,
            failover=failover,
            capture_store=capture_store,
            uow=uow,
            sessions=sessions,
            turns=turns,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
            token_counters=token_counters,
            system_prompt_loader=system_prompt_loader,
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
            raise DomainError(code=ErrorCode.CONFLICT, message=IN_FLIGHT_MESSAGE)

        try:
            return await self._flow.handle(actor=actor, command=command)
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
