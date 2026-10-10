"""Batched Responses construction with source validation and review fallback."""

from uuid import UUID

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
    DocxBuildRoundFailure,
    build_round_request,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_MAX_ROUNDS = 3


class DocxAIConverter:
    """Coordinate at most three failed-source-only rounds into a native exam."""

    def __init__(
        self,
        provider: AnswerKeyStructuredProviderProtocol,
        profile: StructuredLLMProviderProfile,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        enabled: bool,
    ) -> None:
        self._profile = profile
        self._rounds = DocxBuildRoundExchange(provider, leases, uow, clock)
        self._enabled = enabled

    async def convert(
        self,
        *,
        job_id: UUID,
        document_id: UUID,
        filename: str,
        source_sha256: str,
        chunks: tuple[DocxChunk, ...],
        fallback_reason: str | None = None,
    ) -> DocxBuildResult:
        """Freeze converted items and keep every remaining chunk as a reasoned review item."""
        state = DocxBuildState(job_id, document_id, filename, source_sha256, chunks)
        if fallback_reason or not self._enabled:
            reason = fallback_reason or "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
            state.record(
                "fallback", "lease_expired" if fallback_reason else "ai_disabled", detail=reason
            )
            state.fail_all_pending(reason)
            return state.result()
        for round_number in range(1, _MAX_ROUNDS + 1):
            if not state.pending:
                break
            state.round = round_number
            try:
                request = build_round_request(
                    job_id=job_id,
                    round_number=round_number,
                    pending=state.pending,
                    answer_key=tuple(c for c in chunks if c.anchor in state.key_anchors),
                    failures=state.failures,
                    profile=self._profile,
                )
                reply = await self._rounds.exchange(request, self._profile)
            except DocxBuildRoundFailure as error:
                state.record("provider", error.code, detail=error.detail)
                state.fail_all_pending(str(error))
                break
            if reply.reconciliation_failure is not None:
                state.record(
                    "provider", "token_reconciliation_failed", detail=reply.reconciliation_failure
                )
            response = reply.response
            state.record_usage(response.usage)
            if response.finish_reason not in {None, "completed"}:
                state.record(
                    "provider", "response_incomplete", detail=f"status={response.finish_reason}"
                )
                state.fail_all_pending(
                    "AI-tjänstens svar blev ofullständigt. Kontrollera källtexten manuellt."
                )
                break
            admit_batch(response.content, state)
        else:
            if state.pending:
                state.record(
                    "fallback",
                    "retries_exhausted",
                    anchors=tuple(c.anchor for c in state.pending),
                    detail=f"{_MAX_ROUNDS} rounds",
                )
        state.round = None
        return state.result()
