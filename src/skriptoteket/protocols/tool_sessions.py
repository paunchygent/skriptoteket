from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.scripting.tool_sessions import (
    ClearToolSessionStateCommand,
    ClearToolSessionStateResult,
    GetToolSessionStateQuery,
    GetToolSessionStateResult,
    UpdateToolSessionStateCommand,
    UpdateToolSessionStateResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_sessions import ToolSession


class ToolSessionRepositoryProtocol(Protocol):
    async def get(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession | None: ...

    async def get_or_create(
        self,
        *,
        session_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession: ...

    async def update_state(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        expected_state_rev: int,
        state: dict[str, JsonValue],
    ) -> ToolSession: ...

    async def clear_state(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession: ...


class GetToolSessionStateHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: GetToolSessionStateQuery,
    ) -> GetToolSessionStateResult: ...


class UpdateToolSessionStateHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolSessionStateCommand,
    ) -> UpdateToolSessionStateResult: ...


class ClearToolSessionStateHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ClearToolSessionStateCommand,
    ) -> ClearToolSessionStateResult: ...
