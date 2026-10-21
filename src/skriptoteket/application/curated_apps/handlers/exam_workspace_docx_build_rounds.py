"""Batched request construction and provider exchange."""

import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_prompt import (
    docx_build_prompt,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import (
    DOCX_BUILD_SCHEMA_VERSION,
    docx_build_output_spec,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_model_source import marked_source_text
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorCaller, AiJobOverageCapReached
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
)

logger = structlog.get_logger(__name__)


class DocxBuildRoundFailure(Exception):
    """Stop conversion with a Swedish review reason and an observable failure code."""

    def __init__(self, reason: str, *, code: str, detail: str = "") -> None:
        super().__init__(reason)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class DocxRoundReply:
    """Provider response."""

    response: StructuredLLMResponse


class DocxBuildExchangeProtocol(Protocol):
    """The one batch exchange the conversion pipeline and the retry handler depend on.

    ``DocxBuildRoundExchange`` calls the provider behind this method; a test
    double serves one canned reply through the same seam.
    """

    async def exchange(
        self,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> DocxRoundReply: ...


def _model_chunk(chunk: DocxChunk) -> dict[str, str]:
    """Keep source pictures at their marked-text positions without sending their bytes."""
    return {"anchor": chunk.anchor, "kind": chunk.kind, "text": marked_source_text(chunk)}


def build_batch_request(
    *,
    job_id: UUID,
    request_id: str,
    pending: tuple[DocxChunk, ...],
    context: tuple[DocxChunk, ...],
    questions: tuple[tuple[str, ...], ...],
    kinds: frozenset[NativeExamItemKind],
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMRequest:
    """Prepare one batch within the provider's text budget; its schema names its anchors.

    ``questions`` holds each grouped question's own anchors; the payload lists those in
    ``pending``, so the model returns each question as one item.
    """
    spec = docx_build_output_spec(
        anchors=(chunk.anchor for chunk in pending),
        kinds=kinds,
        asset_ids=(image.asset_id for chunk in pending for image in chunk.images),
    )
    payload = json.dumps(
        {
            "item_kinds": sorted(kind.value for kind in kinds),
            "chunks": [_model_chunk(chunk) for chunk in pending],
            "questions": [
                listed
                for question in questions
                if (listed := [chunk.anchor for chunk in pending if chunk.anchor in question])
            ],
            "context_chunks": [_model_chunk(chunk) for chunk in context],
        },
        ensure_ascii=False,
    )
    system_prompt = docx_build_prompt(kinds)
    estimate = estimate_prompt_tokens(system_prompt + payload + json.dumps(spec.json_schema))
    if estimate + profile.max_output_tokens > profile.context_window_tokens:
        raise DocxBuildRoundFailure(
            "Källan ryms inte i AI-tjänstens textbudget. Kontrollera källtexten manuellt.",
            code="text_budget_exceeded",
            detail=f"estimated {estimate} + output {profile.max_output_tokens} "
            f"> context {profile.context_window_tokens}",
        )
    return StructuredLLMRequest(
        job_id=str(job_id),
        item_id=request_id,
        item_type="docx_exam",
        prompt_template_version=DOCX_BUILD_SCHEMA_VERSION,
        system_prompt=system_prompt,
        user_payload=payload,
        output_spec=spec,
        estimated_input_tokens=estimate,
        max_output_tokens=profile.max_output_tokens,
    )


class DocxBuildRoundExchange(DocxBuildExchangeProtocol):
    """Own provider failure handling."""

    def __init__(self, provider: AnswerKeyStructuredProviderProtocol) -> None:
        self._provider = provider

    async def exchange(
        self,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> DocxRoundReply:
        """Call the provider once; a failure stops the batch with a review reason."""
        try:
            response = await self._provider.complete_structured(
                request=request, profile=profile, caller=caller
            )
        except StructuredLLMProviderError as error:
            reason = (
                "AI-tjänsten avböjde tolkningen. Kontrollera källtexten manuellt."
                if error.failure_code.value == "provider_refusal"
                else "AI-tjänsten kunde inte tolka dokumentet "
                f"({error.failure_code.value}). Kontrollera källtexten manuellt."
            )
            raise DocxBuildRoundFailure(
                reason,
                code=error.failure_code.value,
                detail=f"provider={error.provider_id} status={error.status_code}",
            ) from error
        except (AiDailyLimitReached, AiJobOverageCapReached):
            raise
        except Exception as error:
            logger.exception("DOCX build provider unavailable", job_id=request.job_id)
            raise DocxBuildRoundFailure(
                "AI-tjänsten är inte tillgänglig. Kontrollera källtexten manuellt.",
                code="provider_unavailable",
                detail=type(error).__name__,
            ) from error
        return DocxRoundReply(response)
