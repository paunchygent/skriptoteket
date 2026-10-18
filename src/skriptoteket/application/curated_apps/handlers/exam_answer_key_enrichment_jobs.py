"""Worker-side processor for machine answer-key enrichment jobs.

Purpose:
    Complete one claimed enrichment job by dispatching on ``source_kind``:
    the native exam workspace lane, the content-tags processor, the DOCX
    import processor, or the DigiExam import processor. Each lane reserves
    the daily token lease in the same Unit of Work transaction that records
    the enrichment attempt, calls the Luna profile once per unkeyed item with
    at most one GLM failover attempt per item after a transient outage (a
    second lease from the same daily counter), and persists the
    machine-proposed result. Lease exhaustion fail-closes without any
    provider call; it never routes to the failover. The web request never blocks on any of this.

    This handler also fail-closes one RUNNING job whose worker lease
    expired, routed to the same source lane.

Relationships:
    Claimed by the execution worker (``workers.exam_answer_key_enrichment``);
    delegates to ``exam_answer_key_enrichment_workspace_lane``,
    ``exam_workspace_content_tags``, ``exam_workspace_digiexam_jobs`` and
    ``exam_workspace_docx_jobs``. The lanes share
    ``exam_answer_key_enrichment_attempts`` (attempt and lease bookkeeping)
    and the per-item attempt orchestration in
    ``exam_answer_key_provider_attempts``; seams live in
    ``protocols.exam_answer_key``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_attempts import (
    AnswerKeyAttemptLedger,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_workspace_lane import (  # noqa: E501
    ExamAnswerKeyEnrichmentWorkspaceLane,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyProviderAttemptRunner,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ProcessExamAnswerKeyEnrichmentJobHandler:
    """Process one claimed machine answer-key enrichment job to completion."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        provider: AnswerKeyStructuredProviderProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        docx_handler: ProcessExamWorkspaceDocxJobHandler,
        digiexam_handler: ProcessExamWorkspaceDigiExamJobHandler,
        content_tags_handler: ProcessExamContentSuggestionsHandler,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._uow = uow
        self._docx_handler = docx_handler
        self._digiexam_handler = digiexam_handler
        self._content_tags_handler = content_tags_handler
        attempts = AnswerKeyProviderAttemptRunner(
            provider=provider,
            leases=leases,
            uow=uow,
            clock=clock,
        )
        ledger = AnswerKeyAttemptLedger(
            enrichment_jobs=enrichment_jobs,
            leases=leases,
            attempts=attempts,
            uow=uow,
            clock=clock,
        )
        self._workspace_lane = ExamAnswerKeyEnrichmentWorkspaceLane(
            enrichment_jobs=enrichment_jobs,
            provider_selector=provider_selector,
            uow=uow,
            clock=clock,
            ledger=ledger,
        )

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        """Run one claimed enrichment job to a terminal status."""

        match job.source_kind:
            case ExamAnswerKeySourceKind.CONTENT_TAGS:
                return await self._content_tags_handler.handle(job=job)
            case ExamAnswerKeySourceKind.DIGIEXAM_IMPORT:
                return await self._digiexam_handler.handle(job=job)
            case ExamAnswerKeySourceKind.DOCX_IMPORT:
                return await self._docx_handler.handle(job=job)
            case ExamAnswerKeySourceKind.WORKSPACE:
                return await self._workspace_lane.handle(job=job)
        raise ValueError(f"Unsupported enrichment source kind: {job.source_kind!r}")

    async def fail_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Fail-close one RUNNING job whose worker lease expired.

        A crashed worker leaves its job RUNNING past the lease TTL; there is
        no retry, so the job fails closed. Leases already charged stay charged.
        """

        async with self._uow:
            job = await self._enrichment_jobs.claim_next_expired(
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
                source_kind=source_kind,
            )
            if job is None:
                return None
        match job.source_kind:
            case ExamAnswerKeySourceKind.CONTENT_TAGS:
                return await self._content_tags_handler.fail(
                    job=job, last_error="enrichment_worker_lease_expired"
                )
            case ExamAnswerKeySourceKind.DIGIEXAM_IMPORT:
                return await self._digiexam_handler.handle(
                    job=job,
                    fallback_reason="Importen avbröts. Försök importera DigiExam-exporten igen.",
                )
            case ExamAnswerKeySourceKind.DOCX_IMPORT:
                return await self._docx_handler.handle(
                    job=job,
                    fallback_reason="Konverteringen avbröts. Kontrollera innehållet i provet.",
                )
            case ExamAnswerKeySourceKind.WORKSPACE:
                return await self._workspace_lane.fail(
                    job=job, last_error="enrichment_worker_lease_expired"
                )
        raise ValueError(f"Unsupported enrichment source kind: {job.source_kind!r}")
