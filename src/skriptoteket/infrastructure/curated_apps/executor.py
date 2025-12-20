from __future__ import annotations

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.ui.contract_v2 import (
    ToolUiContractV2Result,
    UiFormAction,
    UiIntegerField,
    UiNoticeLevel,
    UiNoticeOutput,
)
from skriptoteket.protocols.curated_apps import CuratedAppExecutorProtocol


def _get_int(*, input: dict[str, JsonValue], key: str, default: int) -> int:
    raw = input.get(key, default)
    if raw is None:
        return default
    if isinstance(raw, bool):
        raise validation_error("Invalid input type", details={"field": key, "expected": "int"})
    if isinstance(raw, int):
        return raw
    raise validation_error(
        "Invalid input type",
        details={"field": key, "expected": "int", "actual": type(raw).__name__},
    )


def _get_counter_state(*, state: dict[str, JsonValue]) -> int:
    raw = state.get("count", 0)
    if raw is None:
        return 0
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    return 0


class InMemoryCuratedAppExecutor(CuratedAppExecutorProtocol):
    async def execute_action(
        self,
        *,
        app: CuratedAppDefinition,
        actor: User,
        action_id: str,
        input: dict[str, JsonValue],
        state: dict[str, JsonValue],
    ) -> ToolUiContractV2Result:
        del actor
        if app.app_id != "demo.counter":
            raise validation_error("Unknown curated app", details={"app_id": app.app_id})

        current = _get_counter_state(state=state)

        if action_id == "start":
            next_count = current
        elif action_id == "increment":
            step = _get_int(input=input, key="step", default=1)
            next_count = current + step
        elif action_id == "reset":
            next_count = 0
        else:
            raise validation_error("Unknown action_id", details={"action_id": action_id})

        return ToolUiContractV2Result(
            status="succeeded",
            error_summary=None,
            outputs=[
                UiNoticeOutput(
                    level=UiNoticeLevel.INFO,
                    message=f"Räknare: {next_count}",
                )
            ],
            next_actions=[
                UiFormAction(
                    action_id="increment",
                    label="Öka",
                    fields=[UiIntegerField(name="step", label="Steg")],
                ),
                UiFormAction(action_id="reset", label="Nollställ", fields=[]),
            ],
            state={"count": next_count},
            artifacts=[],
        )

