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
from skriptoteket.application.curated_apps.classroom_planner.exports.webhook_contract import (
    SEATING_EXPORT_WEBHOOK_EVENT_TYPES,
    build_seating_export_callback_url,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingExportWebhookBindingRepositoryProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmitRequestV2,
    SirConvertWebhookSubscriptionSummaryV2,
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


class CreateSeatingExportJobHandler:
    """Create one async seating export job and submit it to Sir Convert-a-Lot."""

    def __init__(
        self,
        *,
        prepare: PrepareSeatingExportHandler,
        jobs: SeatingExportJobRepositoryProtocol,
        webhook_bindings: SeatingExportWebhookBindingRepositoryProtocol,
        renderer: SeatingPosterRendererProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._prepare = prepare
        self._jobs = jobs
        self._webhook_bindings = webhook_bindings
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
        try:
            job = await self._attach_shared_webhook_binding(
                job=job,
                callback_base_url=callback_base_url,
                correlation_id=correlation_id,
            )
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
            raise

        updated_job = job.model_copy(
            update={
                "status": map_upstream_status(submitted.status),
                "upstream_job_id": submitted.job_id,
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

    async def _attach_shared_webhook_binding(
        self,
        *,
        job: SeatingExportJob,
        callback_base_url: str,
        correlation_id: str | None,
    ) -> SeatingExportJob:
        expected_callback_url = build_seating_export_callback_url(
            callback_base_url=callback_base_url
        )
        async with self._uow:
            shared_binding = await self._webhook_bindings.get_shared_for_update()
            subscriptions = await self._client.list_webhook_subscriptions(
                correlation_id=correlation_id
            )
            canonical_subscriptions = self._canonical_subscriptions(
                subscriptions=subscriptions,
                expected_callback_url=expected_callback_url,
            )
            if self._can_reuse_shared_binding(
                subscription_id=shared_binding.subscription_id,
                callback_url=shared_binding.callback_url,
                secret=shared_binding.secret,
                expected_callback_url=expected_callback_url,
                canonical_subscriptions=canonical_subscriptions,
            ):
                bound_subscription_id = shared_binding.subscription_id
                bound_secret = shared_binding.secret
            else:
                if len(canonical_subscriptions) > 0:
                    raise DomainError(
                        code=ErrorCode.SERVICE_UNAVAILABLE,
                        message=(
                            "Shared seating-export webhook binding is invalid while a "
                            "canonical Sir Convert callback already exists. Run "
                            "`reconcile-seating-export-webhooks` before starting a new "
                            "seating export."
                        ),
                        details={
                            "expected_callback_url": expected_callback_url,
                            "canonical_subscription_ids": [
                                subscription.subscription_id
                                for subscription in canonical_subscriptions
                            ],
                        },
                    )
                subscription = await self._client.create_webhook_subscription(
                    callback_url=expected_callback_url,
                    event_types=list(SEATING_EXPORT_WEBHOOK_EVENT_TYPES),
                    correlation_id=correlation_id,
                )
                shared_binding = await self._webhook_bindings.update_shared(
                    binding=shared_binding.model_copy(
                        update={
                            "subscription_id": subscription.subscription_id,
                            "callback_url": subscription.callback_url,
                            "secret": subscription.secret,
                        }
                    )
                )
                bound_subscription_id = shared_binding.subscription_id
                bound_secret = shared_binding.secret
            return await self._jobs.update(
                job=job.model_copy(
                    update={
                        "webhook_subscription_id": bound_subscription_id,
                        "webhook_secret": bound_secret,
                    }
                )
            )

    def _can_reuse_shared_binding(
        self,
        *,
        subscription_id: str | None,
        callback_url: str | None,
        secret: str | None,
        expected_callback_url: str,
        canonical_subscriptions: tuple[SirConvertWebhookSubscriptionSummaryV2, ...],
    ) -> bool:
        if (
            subscription_id is None
            or callback_url is None
            or secret is None
            or callback_url != expected_callback_url
        ):
            return False
        return any(item.subscription_id == subscription_id for item in canonical_subscriptions)

    def _canonical_subscriptions(
        self,
        *,
        subscriptions: list[SirConvertWebhookSubscriptionSummaryV2],
        expected_callback_url: str,
    ) -> tuple[SirConvertWebhookSubscriptionSummaryV2, ...]:
        return tuple(
            subscription
            for subscription in subscriptions
            if subscription.callback_url == expected_callback_url
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


class _BaseSeatingExportJobReadHandler:
    """Shared read/refresh support for seating export job status handlers."""

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

    async def _build_result(self, *, job: SeatingExportJob) -> SeatingExportJobResult:
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


class GetSeatingExportJobHandler(_BaseSeatingExportJobReadHandler):
    """Load one export job for the owning teacher."""

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
        return await self._build_result(job=job)


class GetRecoverableSeatingExportJobForDraftHandler(_BaseSeatingExportJobReadHandler):
    """Load the latest recoverable export job for the active seating draft."""

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        correlation_id: str | None,
    ) -> SeatingExportJobResult | None:
        in_flight_job = await self._load_latest_in_flight_job(actor=actor, draft_id=draft_id)
        refresh_error: Exception | None = None
        if in_flight_job is not None:
            try:
                refreshed_job = await self._refresh_status(
                    job=in_flight_job,
                    correlation_id=correlation_id,
                )
            except Exception as error:
                refresh_error = error
            else:
                if refreshed_job.status is not SeatingExportJobStatus.FAILED:
                    return await self._build_result(job=refreshed_job)

        downloadable_job = await self._load_latest_downloadable_job(actor=actor, draft_id=draft_id)
        if downloadable_job is None:
            if refresh_error is not None:
                raise refresh_error
            return None
        result = await self._build_result(job=downloadable_job)
        return result if result.download_url is not None else None

    async def _load_latest_in_flight_job(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> SeatingExportJob | None:
        async with self._uow:
            return await self._jobs.get_latest_in_flight_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )

    async def _load_latest_downloadable_job(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> SeatingExportJob | None:
        async with self._uow:
            return await self._jobs.get_latest_downloadable_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )
