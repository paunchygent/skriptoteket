from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import UUID

from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.llm import (
    EditorChatHistoryHandlerProtocol,
    EditorChatHistoryQuery,
    EditorChatHistoryResult,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_THREAD_CONTEXT = "editor_chat"
_THREAD_TTL = timedelta(days=30)
_BASE_VERSION_KEY = "base_version_id"


def _parse_base_version_id(state: Mapping[str, object]) -> UUID | None:
    raw = state.get(_BASE_VERSION_KEY)
    if isinstance(raw, str):
        try:
            return UUID(raw)
        except ValueError:
            return None
    return None


class EditorChatHistoryHandler(EditorChatHistoryHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._messages = messages
        self._clock = clock

    def _is_thread_expired(self, *, last_message_at: datetime) -> bool:
        return self._clock.now() - last_message_at > _THREAD_TTL

    async def handle(
        self,
        *,
        actor: User,
        query: EditorChatHistoryQuery,
    ) -> EditorChatHistoryResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        async with self._uow:
            session = await self._sessions.get(
                tool_id=query.tool_id,
                user_id=actor.id,
                context=_THREAD_CONTEXT,
            )
            if session is None:
                return EditorChatHistoryResult(messages=[], base_version_id=None)

            tail = await self._messages.list_tail(
                tool_session_id=session.id,
                limit=query.limit,
            )

            if tail and self._is_thread_expired(last_message_at=tail[-1].created_at):
                await self._messages.delete_all(tool_session_id=session.id)
                if session.state:
                    await self._sessions.clear_state(
                        tool_id=query.tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                return EditorChatHistoryResult(messages=[], base_version_id=None)

            base_version_id = _parse_base_version_id(session.state)
            return EditorChatHistoryResult(messages=tail, base_version_id=base_version_id)
