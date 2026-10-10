"""Batched Responses construction with source validation and review fallback."""

from dataclasses import replace
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
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class DocxAIConverter:
    """Coordinate at most three failed-source-only rounds into a native exam."""

    def __init__(
        self,
        provider: AnswerKeyStructuredProviderProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        enabled: bool,
    ) -> None:
        self._provider_selector = provider_selector
        self._rounds = DocxBuildRoundExchange(provider, leases, uow, clock)
        self._enabled = enabled

    def _select_profile(self) -> StructuredLLMProviderProfile:
        selected = self._provider_selector.select_route().primary
        if selected.endpoint_kind is not StructuredLLMEndpointKind.RESPONSES:
            raise ValueError("Responses profile required")
        return replace(selected, max_output_tokens=16384)

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
        """Freeze passing items and preserve every remaining source for review."""
        state = DocxBuildState(document_id, filename, source_sha256, chunks)
        if fallback_reason or not self._enabled:
            state.reason = (
                fallback_reason or "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
            )
            return state.result()
        try:
            profile = self._select_profile()
        except Exception:
            state.reason = (
                "AI-tolkningens Responses-tjänst är inte tillgänglig. "
                "Kontrollera källtexten manuellt."
            )
            return state.result()
        for round_number in range(1, 4):
            if not state.pending:
                break
            try:
                request = build_round_request(
                    job_id=job_id,
                    round_number=round_number,
                    pending=state.pending,
                    failures=state.failures,
                    profile=profile,
                )
                response = await self._rounds.exchange(request, profile)
            except DocxBuildRoundFailure as error:
                state.reason = str(error)
                break
            state.record_usage(response.usage)
            if response.finish_reason not in {None, "completed"}:
                state.reason = (
                    "AI-tjänstens svar blev ofullständigt. Kontrollera källtexten manuellt."
                )
                break
            admit_batch(response.content, state)
        return state.result()
