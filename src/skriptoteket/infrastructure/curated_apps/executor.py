from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
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
from skriptoteket.infrastructure.artifacts.filesystem import build_artifacts_manifest
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
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
    def __init__(self, *, artifacts_root: Path) -> None:
        self._artifacts_root = artifacts_root

    def _prepare_run_dir(self, *, run_id: UUID) -> Path:
        run_dir = self._artifacts_root / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def _write_output_bytes(
        self,
        *,
        run_dir: Path,
        output_path: str,
        content: bytes,
    ) -> None:
        relative_path = Path(validate_output_path(path=output_path).as_posix())

        candidate_path = (run_dir / relative_path).resolve()

        run_root = run_dir.resolve()
        artifacts_root = self._artifacts_root.resolve()
        if run_root not in candidate_path.parents:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Artifact path is outside run directory",
                details={"path": output_path},
            )
        if artifacts_root not in candidate_path.parents:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Artifact path is outside artifacts root",
                details={"path": output_path},
            )

        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_bytes(content)

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
        if app.app_id != "demo.counter":
            raise validation_error("Unknown curated app", details={"app_id": app.app_id})

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
            run_dir = self._prepare_run_dir(run_id=run_id)
            self._write_output_bytes(
                run_dir=run_dir,
                output_path="output/counter.txt",
                content=content,
            )
            produced_artifacts = build_artifacts_manifest(run_dir=run_dir)
        else:
            raise validation_error("Unknown action_id", details={"action_id": action_id})

        artifacts = [
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
            artifacts=artifacts,
        )

        return ToolExecutionResult(
            status=RunStatus.SUCCEEDED,
            stdout="",
            stderr="",
            ui_result=ui_result,
            artifacts_manifest=produced_artifacts,
        )
