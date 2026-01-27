from __future__ import annotations

from pydantic import JsonValue

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import (
    ToolUiContractV2Result,
    UiFormAction,
    UiIntegerField,
    UiNoticeLevel,
    UiNoticeOutput,
)
from skriptoteket.infrastructure.curated_apps.artifacts import CuratedAppArtifactWriter


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


async def execute_demo_counter_action(
    *,
    artifacts: CuratedAppArtifactWriter,
    action_id: str,
    input: dict[str, JsonValue],
    state: dict[str, JsonValue],
) -> ToolExecutionResult:
    current = _get_counter_state(state=state)
    produced_artifacts: ArtifactsManifest = ArtifactsManifest(artifacts=[])

    if action_id == "start":
        next_count = current
    elif action_id == "increment":
        step = _get_int(input=input, key="step", default=1)
        next_count = current + step
    elif action_id == "reset":
        next_count = 0
    elif action_id == "export":
        next_count = current
        content = f"Räknare: {next_count}\n".encode("utf-8")
        artifacts.write_bytes(output_path="output/counter.txt", content=content)
        produced_artifacts = artifacts.build_manifest()
    else:
        raise validation_error("Unknown action_id", details={"action_id": action_id})

    artifacts_list = [
        RunnerArtifact(path=artifact.path, bytes=artifact.bytes)
        for artifact in produced_artifacts.artifacts
    ]

    ui_result = ToolUiContractV2Result(
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
            UiFormAction(action_id="export", label="Spara som fil", fields=[]),
        ],
        state={"count": next_count},
        artifacts=artifacts_list,
    )

    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=produced_artifacts,
    )
