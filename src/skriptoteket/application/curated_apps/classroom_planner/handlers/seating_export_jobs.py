"""Application handlers for classroom-planner seating export jobs.

Purpose:
    Orchestrate the PR-0119 export lane: prepare the canonical poster scene,
    render export-owned HTML/CSS, submit conversion jobs to Sir Convert-a-Lot,
    process webhook completion, and deliver the finished PDF from Vault.

Relationships:
    - Reuses `PrepareSeatingExportHandler` from the PR-0118 contract seam.
    - Persists dedicated export jobs through `SeatingExportJobRepositoryProtocol`.
    - Uses the Sir Convert v2 client and Vault protocols for external delivery.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PreparedSeatingExportContract,
    SeatingExportJob,
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmitRequestV2,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

from .seating_export_job_completion import SeatingExportJobFinalizer
from .seating_export_job_support import (
    build_job_result,
    build_job_spec,
    build_resources_zip,
    map_upstream_status,
)
from .seating_exports import PrepareSeatingExportHandler

_WEBHOOK_EVENT_TYPES = ["job.succeeded", "job.failed", "job.canceled"]


class CreateSeatingExportJobHandler:
    """Create one async seating export job and submit it to Sir Convert-a-Lot."""

    def __init__(
        self,
        *,
        prepare: PrepareSeatingExportHandler,
        jobs: SeatingExportJobRepositoryProtocol,
        renderer: SeatingPosterRendererProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._prepare = prepare
        self._jobs = jobs
        self._renderer = renderer
        self._client = client
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._settings = settings

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId,
        paper_size: SeatingExportPaperSize,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        callback_base_url = self._settings.SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL.strip()
        if callback_base_url == "":
            raise validation_error("PDF-export är inte konfigurerad ännu.")

        prepared = await self._prepare.handle(
            draft_id=draft_id,
            owner_user_id=actor.id,
            export_kind=export_kind,
            layout_id=layout_id,
        )
        rendered = self._renderer.render(
            request=SeatingPosterRenderRequest(
                roster_name=prepared.roster_name,
                template_name=prepared.template_name,
                paper_size=paper_size,
                scene=prepared.poster_scene,
            )
        )
        job = await self._create_job_record(
            actor=actor,
            prepared=prepared,
            paper_size=paper_size,
            output_filename=rendered.output_filename,
        )
        callback_url = (
            f"{callback_base_url.rstrip('/')}"
            f"/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs/{job.id}"
        )
        subscription_id: str | None = None
        try:
            subscription = await self._client.create_webhook_subscription(
                callback_url=callback_url,
                event_types=_WEBHOOK_EVENT_TYPES,
                correlation_id=correlation_id,
            )
            subscription_id = subscription.subscription_id
            submitted = await self._client.submit_job(
                request=SirConvertSubmitRequestV2(
                    filename=rendered.html_filename,
                    content_type="text/html",
                    file_bytes=rendered.html_content.encode("utf-8"),
                    resources_filename="resources.zip",
                    resources_bytes=build_resources_zip(
                        filename=rendered.css_filename,
                        content=rendered.css_content.encode("utf-8"),
                    ),
                    job_spec=build_job_spec(
                        paper_size=paper_size,
                        source_filename=rendered.html_filename,
                        css_filename=rendered.css_filename,
                    ),
                    idempotency_key=str(job.id),
                    wait_seconds=0,
                    correlation_id=correlation_id,
                )
            )
        except Exception:
            await self._mark_job_failed(
                job=job,
                error_message="Kunde inte starta PDF-exporten just nu. Försök igen.",
            )
            if subscription_id is not None:
                await self._safe_delete_subscription(
                    subscription_id=subscription_id,
                    correlation_id=correlation_id,
                )
            raise

        updated_job = job.model_copy(
            update={
                "status": map_upstream_status(submitted.status),
                "upstream_job_id": submitted.job_id,
                "webhook_subscription_id": subscription.subscription_id,
                "webhook_secret": subscription.secret,
            }
        )
        async with self._uow:
            updated_job = await self._jobs.update(job=updated_job)
        return await build_job_result(job=updated_job, vault_files=None)

    async def _create_job_record(
        self,
        *,
        actor: User,
        prepared: PreparedSeatingExportContract,
        paper_size: SeatingExportPaperSize,
        output_filename: str,
    ) -> SeatingExportJob:
        now = self._clock.now()
        async with self._uow:
            return await self._jobs.create(
                job=SeatingExportJob(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    draft_id=prepared.seating_draft_id,
                    roster_id=prepared.roster_id,
                    template_id=prepared.template_id,
                    export_kind=prepared.export_kind,
                    layout_id=prepared.layout_id,
                    paper_size=paper_size,
                    output_filename=output_filename,
                    status=SeatingExportJobStatus.SUBMITTED,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _mark_job_failed(self, *, job: SeatingExportJob, error_message: str) -> None:
        async with self._uow:
            await self._jobs.update(
                job=job.model_copy(
                    update={
                        "status": SeatingExportJobStatus.FAILED,
                        "error_message": error_message,
                    }
                )
            )

    async def _safe_delete_subscription(
        self,
        *,
        subscription_id: str,
        correlation_id: str | None,
    ) -> None:
        try:
            await self._client.delete_webhook_subscription(
                subscription_id,
                correlation_id=correlation_id,
            )
        except Exception:
            return


class GetSeatingExportJobHandler:
    """Load one export job for the owning teacher."""

    def __init__(
        self,
        *,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        finalizer: SeatingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._client = client
        self._finalizer = finalizer
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        job = await self._load_owner_job(actor=actor, job_id=job_id)
        if job.status in {SeatingExportJobStatus.SUBMITTED, SeatingExportJobStatus.PROCESSING}:
            job = await self._refresh_status(job=job, correlation_id=correlation_id)
        return await build_job_result(job=job, vault_files=self._vault_files)

    async def _load_owner_job(self, *, actor: User, job_id: UUID) -> SeatingExportJob:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("SeatingExportJob", str(job_id))
        return job

    async def _refresh_status(
        self,
        *,
        job: SeatingExportJob,
        correlation_id: str | None,
    ) -> SeatingExportJob:
        if job.upstream_job_id is None:
            return job
        current = await self._client.get_job(job.upstream_job_id, correlation_id=correlation_id)
        if current.status == "succeeded":
            return await self._finalizer.complete_success(
                job=job,
                correlation_id=correlation_id,
            )
        mapped = map_upstream_status(current.status)
        if mapped is SeatingExportJobStatus.FAILED:
            return await self._finalizer.mark_failed(
                job=job,
                error_message="PDF-exporten kunde inte slutföras.",
                correlation_id=correlation_id,
            )
        if mapped == job.status:
            return job
        updated = job.model_copy(update={"status": mapped})
        async with self._uow:
            return await self._jobs.update(job=updated)
