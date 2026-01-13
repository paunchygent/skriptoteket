from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.llm import (
    EditorChatHistoryHandlerProtocol,
    EditorChatHistoryQuery,
    EditorChatHistoryResult,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_THREAD_CONTEXT = "editor_chat"
_THREAD_TTL = timedelta(days=30)
_BASE_VERSION_KEY = "base_version_id"
_VIRTUAL_FILE_CONTEXT_KIND = "virtual_file_context"


def _parse_base_version_id(state: Mapping[str, object]) -> UUID | None:
    raw = state.get(_BASE_VERSION_KEY)
    if isinstance(raw, str):
        try:
            return UUID(raw)
        except ValueError:
            return None
    return None


def _is_hidden_message(meta: dict[str, JsonValue] | None) -> bool:
    if not isinstance(meta, dict):
        return False
    if meta.get("hidden") is True:
        return True
    return meta.get("kind") == _VIRTUAL_FILE_CONTEXT_KIND


class EditorChatHistoryHandler(EditorChatHistoryHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._turns = turns
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
                return EditorChatHistoryResult(turns=[], messages=[], base_version_id=None)

            fetch_turn_limit = max(1, (query.limit + 1) // 2)
            max_fetch_turn_limit = max(fetch_turn_limit, 1000)

            tail_turns = await self._turns.list_tail(
                tool_session_id=session.id,
                limit=fetch_turn_limit,
            )

            if tail_turns and self._is_thread_expired(last_message_at=tail_turns[-1].created_at):
                await self._turns.delete_all(tool_session_id=session.id)
                if session.state:
                    await self._sessions.clear_state(
                        tool_id=query.tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                return EditorChatHistoryResult(turns=[], messages=[], base_version_id=None)

            base_version_id = _parse_base_version_id(session.state)

            tail_messages = await self._messages.list_by_turn_ids(
                tool_session_id=session.id,
                turn_ids=[turn.id for turn in tail_turns],
            )
            visible = [message for message in tail_messages if not _is_hidden_message(message.meta)]

            while (
                len(visible) < query.limit
                and len(tail_turns) == fetch_turn_limit
                and fetch_turn_limit < max_fetch_turn_limit
            ):
                fetch_turn_limit = min(max_fetch_turn_limit, fetch_turn_limit * 2)
                tail_turns = await self._turns.list_tail(
                    tool_session_id=session.id,
                    limit=fetch_turn_limit,
                )
                tail_messages = await self._messages.list_by_turn_ids(
                    tool_session_id=session.id,
                    turn_ids=[turn.id for turn in tail_turns],
                )
                visible = [
                    message for message in tail_messages if not _is_hidden_message(message.meta)
                ]

            if len(visible) > query.limit:
                visible = visible[-query.limit :]

            return EditorChatHistoryResult(
                turns=tail_turns,
                messages=visible,
                base_version_id=base_version_id,
            )
