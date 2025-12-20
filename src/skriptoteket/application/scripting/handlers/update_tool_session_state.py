from __future__ import annotations

from skriptoteket.application.scripting.tool_sessions import (
    ToolSessionState,
    UpdateToolSessionStateCommand,
    UpdateToolSessionStateResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_sessions import (
    normalize_tool_session_context,
    validate_expected_state_rev,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.tool_sessions import (
    ToolSessionRepositoryProtocol,
    UpdateToolSessionStateHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateToolSessionStateHandler(UpdateToolSessionStateHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolSessionStateCommand,
    ) -> UpdateToolSessionStateResult:
        context = normalize_tool_session_context(context=command.context)
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        async with self._uow:
            await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )
            session = await self._sessions.update_state(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=command.state,
            )

        return UpdateToolSessionStateResult(
            session_state=ToolSessionState(
                tool_id=session.tool_id,
                context=session.context,
                state=session.state,
                state_rev=session.state_rev,
            )
        )

