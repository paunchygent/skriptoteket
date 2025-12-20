from __future__ import annotations

import json

from skriptoteket.application.scripting.commands import ExecuteToolVersionCommand
from skriptoteket.application.scripting.interactive_tools import (
    StartActionCommand,
    StartActionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunContext
from skriptoteket.domain.scripting.tool_sessions import (
    normalize_tool_session_context,
    validate_expected_state_rev,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.interactive_tools import StartActionHandlerProtocol
from skriptoteket.protocols.scripting import ExecuteToolVersionHandlerProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class StartActionHandler(StartActionHandlerProtocol):
    """Start an interactive tool action (ADR-0024).

    The tool receives JSON input bytes with the shape:
    {"action_id": str, "input": {...}, "state": {...}}.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._sessions = sessions
        self._execute = execute
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: StartActionCommand,
    ) -> StartActionResult:
        context = normalize_tool_session_context(context=command.context)
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None or not tool.is_published or tool.active_version_id is None:
                raise not_found("Tool", str(command.tool_id))
            active_version_id = tool.active_version_id
            if active_version_id is None:
                raise not_found("Tool", str(command.tool_id))

            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )
            if session.state_rev != command.expected_state_rev:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="ToolSession state_rev conflict",
                    details={
                        "tool_id": str(command.tool_id),
                        "user_id": str(actor.id),
                        "context": context,
                        "expected_state_rev": command.expected_state_rev,
                        "current_state_rev": session.state_rev,
                    },
                )

            current_state = session.state

        payload = {
            "action_id": command.action_id,
            "input": command.input,
            "state": current_state,
        }
        input_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=tool.id,
                version_id=active_version_id,
                context=RunContext.PRODUCTION,
                input_filename="action.json",
                input_bytes=input_bytes,
            ),
        )

        async with self._uow:
            updated_session = await self._sessions.update_state(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=result.normalized_state,
            )

        return StartActionResult(run_id=result.run.id, state_rev=updated_session.state_rev)
