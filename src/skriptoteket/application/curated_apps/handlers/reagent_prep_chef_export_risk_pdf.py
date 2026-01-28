from __future__ import annotations

import io
import tarfile

from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_helpers import (
    build_risk_export_html,
)
from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefRiskAssessmentRequest,
)
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.curated_apps.reagent_prep_chef.errors import (
    ReagentPrepChefErrorCode,
    rpc_validation_error,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import InputManifest, sanitize_input_filename
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    finish_run,
    start_curated_app_run,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefExportRiskPdfHandlerProtocol,
    ReagentPrepChefPdfRendererProtocol,
    ReagentPrepChefRiskAssessmentHandlerProtocol,
)
from skriptoteket.protocols.runner import ArtifactManagerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

APP_ID = "chemistry.reagent_prep_chef"


def _build_output_archive(*, filename: str, content: bytes) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        info = tarfile.TarInfo(name=f"output/{filename}")
        info.mode = 0o644
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))

    return tar_buffer.getvalue()


def _default_output_filename(*, app: CuratedAppDefinition, filename_hint: str | None) -> str:
    del app

    if filename_hint:
        return sanitize_input_filename(input_filename=filename_hint)

    return "riskbedomning.pdf"


def _missing_context_fields(*, context) -> list[str]:
    if context is None:
        return ["scope", "participants", "approver", "assessment_date", "next_review_date"]

    missing = []
    if not (context.scope or "").strip():
        missing.append("scope")
    if not (context.participants or "").strip():
        missing.append("participants")
    if not (context.approver or "").strip():
        missing.append("approver")
    if context.assessment_date is None:
        missing.append("assessment_date")
    if context.next_review_date is None:
        missing.append("next_review_date")
    return missing


class ReagentPrepChefExportRiskPdfHandler(ReagentPrepChefExportRiskPdfHandlerProtocol):
    def __init__(
        self,
        *,
        risk: ReagentPrepChefRiskAssessmentHandlerProtocol,
        pdf: ReagentPrepChefPdfRendererProtocol,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        artifacts: ArtifactManagerProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._risk = risk
        self._pdf = pdf
        self._uow = uow
        self._runs = runs
        self._artifacts = artifacts
        self._curated_apps = curated_apps
        self._clock = clock
        self._id_generator = id_generator

    async def _record_run(
        self,
        *,
        actor: User,
        app: CuratedAppDefinition,
        pdf_bytes: bytes,
        output_filename: str,
    ) -> None:
        now = self._clock.now()
        run_id = self._id_generator.new_uuid()

        run = start_curated_app_run(
            run_id=run_id,
            tool_id=app.tool_id,
            curated_app_id=app.app_id,
            curated_app_version=app.app_version,
            context=RunContext.PRODUCTION,
            requested_by_user_id=actor.id,
            session_context="default",
            workdir_path=str(run_id),
            input_filename=None,
            input_size_bytes=0,
            input_manifest=InputManifest(),
            now=now,
        )

        async with self._uow:
            await self._runs.create(run=run)

        output_archive = _build_output_archive(filename=output_filename, content=pdf_bytes)
        manifest = self._artifacts.store_output_archive(
            run_id=run_id,
            output_archive=[output_archive],
            reported_artifacts=[],
        )

        finished = finish_run(
            run=run,
            status=RunStatus.SUCCEEDED,
            now=self._clock.now(),
            stdout="",
            stderr="",
            artifacts_manifest=manifest.model_dump(),
            error_summary=None,
            ui_payload=None,
        )

        async with self._uow:
            await self._runs.update(run=finished)

    async def handle(self, *, actor: User, command: ReagentPrepChefRiskAssessmentRequest) -> bytes:
        app = self._curated_apps.get_by_app_id(app_id=APP_ID)
        if app is None:
            raise not_found("CuratedApp", APP_ID)

        result = await self._risk.handle(actor=actor, command=command)
        draft = result.draft

        if draft.requires_confirmation:
            raise rpc_validation_error(
                app_code=ReagentPrepChefErrorCode.RISK_CONFIRMATION_REQUIRED,
                message="Bekräfta alla risker innan export.",
                details={"missing_confirmations": draft.missing_confirmations},
            )

        missing_context = _missing_context_fields(context=draft.context)
        if missing_context:
            raise rpc_validation_error(
                app_code=ReagentPrepChefErrorCode.RISK_CONTEXT_INCOMPLETE,
                message="Fyll i obligatoriska fält innan export.",
                details={"missing_fields": missing_context},
            )

        export_html = build_risk_export_html(draft=draft, warnings=result.warnings)
        try:
            pdf_bytes = self._pdf.render_html(html=export_html)
        except Exception as exc:  # noqa: BLE001
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte skapa PDF just nu. Försök igen.",
                details={},
            ) from exc

        output_filename = _default_output_filename(
            app=app,
            filename_hint="riskbedomning.pdf",
        )
        try:
            await self._record_run(
                actor=actor, app=app, pdf_bytes=pdf_bytes, output_filename=output_filename
            )
        except Exception as exc:  # noqa: BLE001
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte skapa PDF just nu. Försök igen.",
                details={},
            ) from exc

        return pdf_bytes
