from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result


class CuratedAppRegistryProtocol(Protocol):
    def list_all(self) -> list[CuratedAppDefinition]: ...

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None: ...

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None: ...


class CuratedAppExecutorProtocol(Protocol):
    async def execute_action(
        self,
        *,
        app: CuratedAppDefinition,
        actor: User,
        action_id: str,
        input: dict[str, JsonValue],
        state: dict[str, JsonValue],
    ) -> ToolUiContractV2Result: ...

