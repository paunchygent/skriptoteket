from __future__ import annotations

from skriptoteket.application.scripting.tool_sessions import (
    GetToolSessionStateQuery,
    GetToolSessionStateResult,
    ToolSessionState,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.tool_sessions import (
    GetToolSessionStateHandlerProtocol,
    ToolSessionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class GetToolSessionStateHandler(GetToolSessionStateHandlerProtocol):
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
        query: GetToolSessionStateQuery,
    ) -> GetToolSessionStateResult:
        context = normalize_tool_session_context(context=query.context)

        async with self._uow:
            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=query.tool_id,
                user_id=actor.id,
                context=context,
            )

        return GetToolSessionStateResult(
            session_state=ToolSessionState(
                tool_id=session.tool_id,
                context=session.context,
                state=session.state,
                state_rev=session.state_rev,
            )
        )
