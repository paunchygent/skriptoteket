"""Protocol seams for the exam answer-key completion vertical.

Purpose:
    Keep the machine answer-key lane protocol-first: structured provider
    execution, provider selection, and the enrichment job ledger all sit
    behind protocols so infrastructure can evolve independently.

Relationships:
    Implemented under ``infrastructure.llm.openai`` and
    ``infrastructure.repositories``; consumed by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs`` and
    the execution worker. The provider-selection protocol yields the ordered
    Luna-primary/GLM-failover route decided by TASK-SKRIPT-39-02-02.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
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
    """Select the ordered primary/failover provider route for one job."""

    def select_route(self) -> AnswerKeyProviderRoute: ...


class ExamAnswerKeyEnrichmentJobRepositoryProtocol(Protocol):
    """Persist and claim machine answer-key enrichment jobs."""

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob: ...

    async def update(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        expected_worker_id: str | None = None,
    ) -> ExamAnswerKeyEnrichmentJob: ...

    async def set_conversion_progress(
        self, *, job_id: UUID, progress: dict[str, JsonValue]
    ) -> None:
        """Replace the job's persisted conversion progress; update never writes it."""
        ...

    async def get_conversion_view(self, *, job_id: UUID) -> ExamWorkspaceConversionJobView | None:
        """Read the status-poll columns only; never loads the uploaded source bytes."""
        ...

    async def lock_conversion_view_by_lineage(
        self, *, owner_user_id: UUID, workspace_lineage_id: UUID
    ) -> ExamWorkspaceConversionJobView | None:
        """Read and share-lock the DOCX import job that created a document lineage.

        The lock holds conversion back until the caller's transaction ends, so a document
        head read in that transaction matches the job's progress.
        """
        ...

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        """Read one job by id without locking it."""
        ...

    async def get_by_id_for_update(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        """Lock and refresh the row before publishing a worker's terminal result."""
        ...

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None: ...

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Take one RUNNING job whose worker lease expired, for fail-closing."""
        ...

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool: ...


class ExamWorkspaceSuggestionJobQueryProtocol(Protocol):
    """Find workspace suggestion jobs by the saved version they were requested on."""

    async def get_latest_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Read the newest suggestion job requested against one saved version."""
        ...

    async def get_active_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
        workspace_request_json: dict[str, JsonValue],
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Read a queued or running suggestion job on exactly this sent content."""
        ...

    async def lock_workspace_requests(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> None:
        """Serialize suggestion requests on one saved version until the transaction ends.

        Taken inside the caller's unit of work before the active-job lookup,
        so that lookup and the enqueue that may follow are one decision.
        """
        ...
