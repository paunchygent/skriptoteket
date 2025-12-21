from __future__ import annotations

from typing import Protocol

from skriptoteket.application.scripting.interactive_tools import (
    GetRunQuery,
    GetRunResult,
    GetSessionStateQuery,
    GetSessionStateResult,
    ListArtifactsQuery,
    ListArtifactsResult,
    StartActionCommand,
    StartActionResult,
)
from skriptoteket.domain.identity.models import User


class StartActionHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, command: StartActionCommand) -> StartActionResult: ...


class GetSessionStateHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: GetSessionStateQuery,
    ) -> GetSessionStateResult: ...


class GetRunHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: GetRunQuery) -> GetRunResult: ...


class ListArtifactsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListArtifactsQuery,
    ) -> ListArtifactsResult: ...
