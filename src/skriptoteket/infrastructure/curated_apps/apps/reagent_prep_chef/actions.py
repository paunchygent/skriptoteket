from __future__ import annotations

from pydantic import JsonValue, ValidationError

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import (
    ToolUiContractV2Result,
    UiNoticeLevel,
    UiNoticeOutput,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.defaults import default_inputs
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.models import PrepRequest
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.prep_sheet import (
    build_prep_sheet,
)
from skriptoteket.infrastructure.curated_apps.artifacts import CuratedAppArtifactWriter


async def execute_reagent_prep_chef_action(
    *,
    artifacts: CuratedAppArtifactWriter,
    action_id: str,
    input: dict[str, JsonValue],
    state: dict[str, JsonValue],
) -> ToolExecutionResult:
    if action_id == "reset":
        return _handle_reset()
    if action_id == "start":
        return _handle_start(state=state)
    if action_id == "export_pdf":
        return _handle_export_pdf(artifacts=artifacts, state=state)
    if action_id == "calculate":
        return _handle_calculate(input=input)
    return _build_error_result(message="Okänd åtgärd.", inputs=None)


def _handle_reset() -> ToolExecutionResult:
    ui_result = ToolUiContractV2Result(
        status="succeeded",
        error_summary=None,
        outputs=[UiNoticeOutput(level=UiNoticeLevel.INFO, message="Nollställt.")],
        next_actions=[],
        state={},
        artifacts=[],
    )
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )


def _handle_start(*, state: dict[str, JsonValue]) -> ToolExecutionResult:
    existing_inputs = state.get("inputs") if isinstance(state.get("inputs"), dict) else None

    state_out: dict[str, JsonValue] = {
        "inputs": existing_inputs if isinstance(existing_inputs, dict) else default_inputs(),
    }

    ui_result = ToolUiContractV2Result(
        status="succeeded",
        error_summary=None,
        outputs=[
            UiNoticeOutput(
                level=UiNoticeLevel.INFO,
                message="Fyll i uppgifterna och kör Beräkna i den anpassade vyn.",
            )
        ],
        next_actions=[],
        state=state_out,
        artifacts=[],
    )
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )


def _handle_export_pdf(
    *,
    artifacts: CuratedAppArtifactWriter,
    state: dict[str, JsonValue],
) -> ToolExecutionResult:
    export_html = state.get("export_html")
    if not isinstance(export_html, str) or not export_html.strip():
        return _build_error_result(
            message="Det finns inget att exportera ännu. Kör en beräkning först.",
            inputs=None,
        )

    try:
        from weasyprint import HTML  # type: ignore

        pdf_bytes = HTML(string=export_html).write_pdf()
    except Exception:
        return _build_error_result(
            message="Kunde inte skapa PDF just nu. Försök igen.",
            inputs=None,
        )

    artifacts.write_bytes(output_path="output/reagensberedning.pdf", content=pdf_bytes)
    produced = artifacts.build_manifest()
    artifacts_list = [
        RunnerArtifact(path=artifact.path, bytes=artifact.bytes) for artifact in produced.artifacts
    ]

    ui_result = ToolUiContractV2Result(
        status="succeeded",
        error_summary=None,
        outputs=[UiNoticeOutput(level=UiNoticeLevel.INFO, message="PDF skapad.")],
        next_actions=[],
        state=None,
        artifacts=artifacts_list,
    )
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=produced,
    )


def _handle_calculate(*, input: dict[str, JsonValue]) -> ToolExecutionResult:
    try:
        request = PrepRequest.model_validate(input)
    except ValidationError as exc:
        return _build_error_result(
            message=_format_validation_error(exc),
            inputs=input,
        )

    try:
        sheet = build_prep_sheet(request=request)
    except Exception:  # noqa: BLE001
        return _build_error_result(
            message="Vi kunde inte tolka formeln. Kontrollera stavning och hydratnotation.",
            inputs=input,
        )

    ui_result = ToolUiContractV2Result(
        status="succeeded",
        error_summary=None,
        outputs=sheet.outputs,
        next_actions=[],
        state=sheet.state,
        artifacts=[],
    )
    return ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )


def _build_error_result(
    *,
    message: str,
    inputs: dict[str, JsonValue] | None,
) -> ToolExecutionResult:
    state: dict[str, JsonValue] | None = None
    if inputs is not None:
        state = {"inputs": inputs}

    ui_result = ToolUiContractV2Result(
        status="failed",
        error_summary=message,
        outputs=[
            UiNoticeOutput(
                level=UiNoticeLevel.ERROR,
                message=message,
            )
        ],
        next_actions=[],
        state=state,
        artifacts=[],
    )
    return ToolExecutionResult(
        status=RunStatus.FAILED,
        stdout="",
        stderr="",
        ui_result=ui_result,
        artifacts_manifest=ArtifactsManifest(artifacts=[]),
    )


def _format_validation_error(exc: ValidationError) -> str:
    issues: list[str] = []
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", []) if part is not None)
        message = item.get("msg", "Ogiltigt värde")
        issues.append(f"- {location}: {message}" if location else f"- {message}")
    if not issues:
        return "Ogiltiga indata."
    return "Ogiltiga indata:\n" + "\n".join(issues)
