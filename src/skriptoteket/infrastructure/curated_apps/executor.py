from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.infrastructure.curated_apps.apps.demo_counter import execute_demo_counter_action
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import (
    execute_reagent_prep_chef_action,
)
from skriptoteket.infrastructure.curated_apps.artifacts import CuratedAppArtifactWriter
from skriptoteket.protocols.curated_apps import CuratedAppExecutorProtocol


class CuratedAppHandler(Protocol):
    async def __call__(
        self,
        *,
        artifacts: CuratedAppArtifactWriter,
        action_id: str,
        input: dict[str, JsonValue],
        state: dict[str, JsonValue],
    ) -> ToolExecutionResult: ...


_HANDLERS: dict[str, CuratedAppHandler] = {
    "demo.counter": execute_demo_counter_action,
    "chemistry.reagent_prep_chef": execute_reagent_prep_chef_action,
}


class InMemoryCuratedAppExecutor(CuratedAppExecutorProtocol):
    def __init__(self, *, artifacts_root: Path) -> None:
        self._artifacts_root = artifacts_root

    async def execute_action(
        self,
        *,
        run_id: UUID,
        app: CuratedAppDefinition,
        actor: User,
        action_id: str,
        input: dict[str, JsonValue],
        state: dict[str, JsonValue],
    ) -> ToolExecutionResult:
        del actor

        handler = _HANDLERS.get(app.app_id)
        if handler is None:
            raise validation_error("Unknown curated app", details={"app_id": app.app_id})

        artifacts = CuratedAppArtifactWriter(artifacts_root=self._artifacts_root, run_id=run_id)
        return await handler(
            artifacts=artifacts,
            action_id=action_id,
            input=input,
            state=state,
        )
