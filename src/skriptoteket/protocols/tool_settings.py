from __future__ import annotations

from typing import Protocol

from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    GetToolSettingsResult,
    UpdateToolSettingsCommand,
    UpdateToolSettingsResult,
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

