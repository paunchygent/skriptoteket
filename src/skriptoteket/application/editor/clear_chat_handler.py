from __future__ import annotations

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import EditorChatClearCommand, EditorChatClearHandlerProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_THREAD_CONTEXT = "editor_chat"


class EditorChatClearHandler(EditorChatClearHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._messages = messages

    async def handle(self, *, actor: User, command: EditorChatClearCommand) -> None:
        async with self._uow:
            session = await self._sessions.get(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=_THREAD_CONTEXT,
            )
            if session is None:
                return

            await self._messages.delete_all(tool_session_id=session.id)
            if session.state:
                await self._sessions.clear_state(
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=_THREAD_CONTEXT,
                )
