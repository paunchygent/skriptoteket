from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    GetToolSettingsResult,
    GetToolVersionSettingsQuery,
    GetToolVersionSettingsResult,
    ResolveSandboxSettingsQuery,
    ResolveSandboxSettingsResult,
    SaveSandboxSettingsCommand,
    SaveSandboxSettingsResult,
    ToolSettingsState,
    UpdateToolSettingsCommand,
    UpdateToolSettingsResult,
    UpdateToolVersionSettingsCommand,
    UpdateToolVersionSettingsResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_settings import ToolSettingsSchema, ToolSettingsValues


class GetToolSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: GetToolSettingsQuery,
    ) -> GetToolSettingsResult: ...


class UpdateToolSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolSettingsCommand,
    ) -> UpdateToolSettingsResult: ...


class GetToolVersionSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: GetToolVersionSettingsQuery,
    ) -> GetToolVersionSettingsResult: ...


class UpdateToolVersionSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolVersionSettingsCommand,
    ) -> UpdateToolVersionSettingsResult: ...


class ResolveSandboxSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ResolveSandboxSettingsQuery,
    ) -> ResolveSandboxSettingsResult: ...


class SaveSandboxSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: SaveSandboxSettingsCommand,
    ) -> SaveSandboxSettingsResult: ...


class ToolSettingsServiceProtocol(Protocol):
    async def resolve_sandbox_settings(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        draft_head_id: UUID,
        settings_schema: ToolSettingsSchema,
    ) -> ToolSettingsState: ...

    async def save_sandbox_settings(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        draft_head_id: UUID,
        settings_schema: ToolSettingsSchema,
        expected_state_rev: int,
        values: ToolSettingsValues,
    ) -> ToolSettingsState: ...
