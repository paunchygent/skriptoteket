from __future__ import annotations

from skriptoteket.application.scripting.interactive_tools import (
    GetSessionStateQuery,
    GetSessionStateResult,
    InteractiveSessionState,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunContext
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.interactive_tools import GetSessionStateHandlerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class GetSessionStateHandler(GetSessionStateHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._sessions = sessions
        self._runs = runs
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        query: GetSessionStateQuery,
    ) -> GetSessionStateResult:
        context = normalize_tool_session_context(context=query.context)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=query.tool_id)
            if tool is None or not tool.is_published or tool.active_version_id is None:
                raise not_found("Tool", str(query.tool_id))

            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=query.tool_id,
                user_id=actor.id,
                context=context,
            )
            latest_run = await self._runs.get_latest_for_user_and_tool(
                user_id=actor.id,
                tool_id=query.tool_id,
                context=RunContext.PRODUCTION,
            )

        return GetSessionStateResult(
            session_state=InteractiveSessionState(
                tool_id=session.tool_id,
                context=session.context,
                state=session.state,
                state_rev=session.state_rev,
                latest_run_id=None if latest_run is None else latest_run.id,
            )
        )

