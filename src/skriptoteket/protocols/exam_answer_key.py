"""Protocol seams for the exam answer-key completion vertical.

Purpose:
    Keep the machine answer-key lane protocol-first: structured provider
    execution, provider selection, the Postgres daily token lease, the
    enrichment job ledger, and proposed-overlay persistence all sit behind
    protocols so infrastructure can evolve independently.

Relationships:
    Implemented under ``infrastructure.llm.openai`` and
    ``infrastructure.repositories``; consumed by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs`` and
    the execution worker. The provider-selection protocol is the seam
    TASK-SKRIPT-39-02-02 extends with failover; it stays Luna-only here.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyProposedOverlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
)


class AnswerKeyStructuredProviderProtocol(Protocol):
    """Execute one structured answer-key request against a provider profile."""

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse: ...


class AnswerKeyProviderSelectorProtocol(Protocol):
    """Select the provider profile for one enrichment attempt.

    TASK-SKRIPT-39-02-01 ships a Luna-only selection; the failover order in
    TASK-SKRIPT-39-02-02 extends this seam without touching callers.
    """

    def select_profile(self) -> StructuredLLMProviderProfile: ...


class AnswerKeyTokenLeaseRepositoryProtocol(Protocol):
    """Own the single Postgres daily token-lease table through the UoW.

    ``reserve`` raises ``AnswerKeyTokenLeaseRefused`` when the UTC day's
    remaining allowance cannot cover ``requested_tokens``. Leases are never
    refunded: an unreconciled lease keeps charging its reserved amount.
    """

    async def reserve(
        self,
        *,
        now: datetime,
        requested_tokens: int,
        job_id: UUID,
        item_id: str,
        provider_profile_id: str,
    ) -> AnswerKeyTokenLease: ...

    async def reconcile(
        self,
        *,
        lease_id: UUID,
        actual_tokens: int,
        now: datetime,
    ) -> None: ...

    async def day_usage(self, *, utc_day: date) -> AnswerKeyTokenLeaseDayUsage: ...


class ExamAnswerKeyEnrichmentJobRepositoryProtocol(Protocol):
    """Persist and claim machine answer-key enrichment jobs."""

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob: ...

    async def update(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob: ...

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None: ...

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> ExamAnswerKeyEnrichmentJob | None: ...

    async def claim_next_expired(
        self,
        *,
        now: datetime,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Take one RUNNING job whose worker lease expired, for fail-closing."""
        ...


class ExamAnswerKeyProposedOverlayRepositoryProtocol(Protocol):
    """Persist machine-proposed answer-key overlays as proposal records."""

    async def create(
        self,
        *,
        proposed_overlay: ExamAnswerKeyProposedOverlay,
    ) -> ExamAnswerKeyProposedOverlay: ...

    async def get_by_conversion_job_id(
        self,
        *,
        conversion_job_id: UUID,
    ) -> ExamAnswerKeyProposedOverlay | None: ...
