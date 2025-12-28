from __future__ import annotations

from typing import Protocol

from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    GetToolSettingsResult,
    GetToolVersionSettingsQuery,
    GetToolVersionSettingsResult,
    UpdateToolSettingsCommand,
    UpdateToolSettingsResult,
    UpdateToolVersionSettingsCommand,
    UpdateToolVersionSettingsResult,
)
from skriptoteket.domain.identity.models import User


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
