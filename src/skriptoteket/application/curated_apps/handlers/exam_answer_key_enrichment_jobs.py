"""Worker-side processor for machine answer-key enrichment jobs.

Purpose:
    Complete one claimed enrichment job: reserve the daily token lease in the
    same Unit of Work transaction that records the enrichment attempt, call
    the Luna profile once per unkeyed item, persist the machine-proposed
    overlay, and finish the owning conversion with unchanged readiness
    semantics. The web request never blocks on any of this.

Relationships:
    Claimed by the execution worker (``workers.exam_answer_key_enrichment``);
    uses the protocol seams in ``protocols.exam_answer_key`` and the existing
    in-process producer and artifact store.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    finish_enrichment_job,
    record_enrichment_attempt,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    build_local_exam_conversion_producer_id,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    parse_source_exam,
    source_exam_digests,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyCandidatePlan,
    AnswerKeyEnrichmentPlanState,
    build_machine_proposed_overlay,
    manual_answer_key_from_model_content,
    overlay_json_bytes,
    plan_answer_key_candidates,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
    requested_lease_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlay,
    DigiExamOverlayManualAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIrItem,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    InProcessExamConverterProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)

_DXE_CONTENT_TYPE = "application/octet-stream"
_MANUAL_COMPLETION_MESSAGE = (
    "Provet kunde inte kompletteras automatiskt med facit. "
    "Komplettera facit manuellt och försök igen."
)
_PROVIDER_FAILURE_MESSAGE = "Facitförslaget kunde inte hämtas just nu. Försök igen senare."


class ProcessExamAnswerKeyEnrichmentJobHandler:
    """Process one claimed machine answer-key enrichment job to completion."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        conversion_jobs: ConversionHubJobRepositoryProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        provider: AnswerKeyStructuredProviderProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._conversion_jobs = conversion_jobs
        self._leases = leases
        self._proposed_overlays = proposed_overlays
        self._provider = provider
        self._provider_selector = provider_selector
        self._producer = producer
        self._artifacts = artifacts
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        """Run one claimed enrichment job to a terminal status."""

        upload = ConversionHubUpload(
            filename=job.input_filename,
            content_type=_DXE_CONTENT_TYPE,
            file_bytes=job.source_dxe,
        )
        try:
            exam = parse_source_exam(upload=upload)
        except DomainError as exc:
            return await self._fail(job=job, teacher_message=exc.message, last_error="parse_failed")
        plan = plan_answer_key_enrichment(exam)
        if plan.state is not AnswerKeyEnrichmentPlanState.ELIGIBLE:
            return await self._fail(
                job=job,
                teacher_message=_MANUAL_COMPLETION_MESSAGE,
                last_error=f"enrichment_plan_{plan.state.value}",
            )
        profile = self._provider_selector.select_profile()
        candidates = plan_answer_key_candidates(
            job_id=str(job.conversion_job_id),
            items=plan.unkeyed_items,
            profile=profile,
        )

        try:
            job, leases_by_item = await self._record_attempt_and_reserve(
                job=job,
                candidates=candidates,
                profile=profile,
            )
        except AnswerKeyTokenLeaseRefused as refusal:
            return await self._fail(
                job=job,
                teacher_message=(
                    "Dagens AI-budget för facitförslag är förbrukad. Försök igen efter "
                    f"{refusal.resets_at:%Y-%m-%d %H:%M} UTC."
                ),
                last_error="daily_token_lease_exhausted",
            )

        proposals, failure = await self._collect_proposals(
            candidates=candidates,
            profile=profile,
            leases_by_item=leases_by_item,
        )
        if failure is not None:
            return await self._fail(
                job=job,
                teacher_message=failure.teacher_message,
                last_error=failure.last_error,
            )

        source_file_sha256, source_ir_sha256 = source_exam_digests(
            file_bytes=job.source_dxe,
            exam=exam,
        )
        overlay = build_machine_proposed_overlay(
            source_file_sha256=source_file_sha256,
            source_ir_sha256=source_ir_sha256,
            proposals=proposals,
        )
        try:
            artifact = await self._producer.convert(
                upload=upload,
                overlay_bytes=overlay_json_bytes(overlay),
                correlation_id=None,
                overlay_key_provenance=DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY,
            )
            self._artifacts.store_artifact(job_id=job.conversion_job_id, artifact=artifact)
        except DomainError as exc:
            return await self._fail(
                job=job,
                teacher_message=exc.message,
                last_error="conversion_failed_after_proposals",
            )
        return await self._succeed(
            job=job,
            overlay=overlay,
            profile=profile,
            source_file_sha256=source_file_sha256,
            source_ir_sha256=source_ir_sha256,
        )

    async def fail_next_expired(self, *, now: datetime) -> ExamAnswerKeyEnrichmentJob | None:
        """Fail-close one RUNNING job whose worker lease expired.

        A crashed worker leaves its job RUNNING past the lease TTL; there is
        no retry, so the job and its owning conversion fail closed in one
        transaction. Leases already charged stay charged.
        """

        async with self._uow:
            job = await self._enrichment_jobs.claim_next_expired(now=now)
            if job is None:
                return None
            await self._update_conversion_job(
                conversion_job_id=job.conversion_job_id,
                status=ConversionHubJobStatus.FAILED,
                error_message=_MANUAL_COMPLETION_MESSAGE,
                now=now,
            )
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    now=now,
                    last_error="enrichment_worker_lease_expired",
                )
            )

    async def _record_attempt_and_reserve(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        candidates: tuple[AnswerKeyCandidatePlan, ...],
        profile: StructuredLLMProviderProfile,
    ) -> tuple[ExamAnswerKeyEnrichmentJob, dict[str, AnswerKeyTokenLease]]:
        """Reserve every candidate's lease with the recorded attempt, atomically.

        A refusal aborts the transaction, so an exhausted day records neither
        an attempt nor any partial reservation and no provider call is made.
        """

        now = self._clock.now()
        leases_by_item: dict[str, AnswerKeyTokenLease] = {}
        async with self._uow:
            updated_job = await self._enrichment_jobs.update(
                job=record_enrichment_attempt(job=job, now=now)
            )
            for candidate in candidates:
                leases_by_item[candidate.item.item_id] = await self._leases.reserve(
                    now=now,
                    requested_tokens=requested_lease_tokens(
                        estimated_input_tokens=candidate.request.estimated_input_tokens,
                        max_output_tokens=candidate.request.max_output_tokens,
                    ),
                    job_id=updated_job.id,
                    item_id=candidate.item.item_id,
                    provider_profile_id=profile.provider_id,
                )
        return updated_job, leases_by_item

    async def _collect_proposals(
        self,
        *,
        candidates: tuple[AnswerKeyCandidatePlan, ...],
        profile: StructuredLLMProviderProfile,
        leases_by_item: dict[str, AnswerKeyTokenLease],
    ) -> tuple[
        tuple[tuple[DigiExamIrItem, DigiExamOverlayManualAnswerKey], ...],
        "_EnrichmentFailure | None",
    ]:
        proposals: list[tuple[DigiExamIrItem, DigiExamOverlayManualAnswerKey]] = []
        for candidate in candidates:
            try:
                response = await self._provider.complete_structured(
                    request=candidate.request,
                    profile=profile,
                )
            except StructuredLLMProviderError as exc:
                logger.warning(
                    "Answer-key provider attempt failed",
                    extra={
                        "item_id": candidate.item.item_id,
                        "provider_id": exc.provider_id,
                        "failure_code": exc.failure_code.value,
                        "status_code": exc.status_code,
                    },
                )
                return (), _EnrichmentFailure(
                    teacher_message=_PROVIDER_FAILURE_MESSAGE,
                    last_error=exc.failure_code.value,
                )
            usable_tokens = response.usage.usable_total_tokens
            if usable_tokens is not None:
                now = self._clock.now()
                async with self._uow:
                    await self._leases.reconcile(
                        lease_id=leases_by_item[candidate.item.item_id].lease_id,
                        actual_tokens=usable_tokens,
                        now=now,
                    )
            key = manual_answer_key_from_model_content(
                item=candidate.item,
                content=response.content,
            )
            if key is None:
                return (), _EnrichmentFailure(
                    teacher_message=_MANUAL_COMPLETION_MESSAGE,
                    last_error="llm_output_invalid",
                )
            proposals.append((candidate.item, key))
        return tuple(proposals), None

    async def _succeed(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        overlay: DigiExamIngestionOverlay,
        profile: StructuredLLMProviderProfile,
        source_file_sha256: str,
        source_ir_sha256: str,
    ) -> ExamAnswerKeyEnrichmentJob:
        now = self._clock.now()
        async with self._uow:
            await self._proposed_overlays.create(
                proposed_overlay=ExamAnswerKeyProposedOverlay(
                    id=self._id_generator.new_uuid(),
                    enrichment_job_id=job.id,
                    conversion_job_id=job.conversion_job_id,
                    owner_user_id=job.owner_user_id,
                    source_file_sha256=source_file_sha256,
                    source_ir_sha256=source_ir_sha256,
                    provider_profile_id=profile.provider_id,
                    model=profile.model,
                    overlay_json=overlay.model_dump(mode="json"),
                    created_at=now,
                )
            )
            await self._update_conversion_job(
                conversion_job_id=job.conversion_job_id,
                status=ConversionHubJobStatus.SUCCEEDED,
                error_message=None,
                now=now,
            )
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=now,
                )
            )

    async def _fail(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        teacher_message: str,
        last_error: str,
    ) -> ExamAnswerKeyEnrichmentJob:
        now = self._clock.now()
        async with self._uow:
            await self._update_conversion_job(
                conversion_job_id=job.conversion_job_id,
                status=ConversionHubJobStatus.FAILED,
                error_message=teacher_message,
                now=now,
            )
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    now=now,
                    last_error=last_error,
                )
            )

    async def _update_conversion_job(
        self,
        *,
        conversion_job_id: UUID,
        status: ConversionHubJobStatus,
        error_message: str | None,
        now: datetime,
    ) -> ConversionHubJob | None:
        conversion_job = await self._conversion_jobs.get_by_id(job_id=conversion_job_id)
        if conversion_job is None:
            logger.warning(
                "Conversion job missing for enrichment result",
                extra={"conversion_job_id": str(conversion_job_id)},
            )
            return None
        upstream_job_id = conversion_job.upstream_job_id
        if status is ConversionHubJobStatus.SUCCEEDED:
            upstream_job_id = build_local_exam_conversion_producer_id(job_id=conversion_job.id)
        return await self._conversion_jobs.update(
            job=conversion_job.model_copy(
                update={
                    "status": status,
                    "error_message": error_message,
                    "upstream_job_id": upstream_job_id,
                    "updated_at": now,
                }
            )
        )


@dataclass(frozen=True)
class _EnrichmentFailure:
    """Terminal per-job failure with the teacher-facing message."""

    teacher_message: str
    last_error: str
