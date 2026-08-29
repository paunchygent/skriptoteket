"""Endpoint-kind dispatch for answer-key structured providers.

Purpose:
    Route one structured answer-key request to the adapter that owns the
    profile's endpoint family, so the enrichment handler keeps a single
    provider seam across the Luna (Responses) and GLM (Chat Completions)
    profiles.

Relationships:
    Implements ``protocols.exam_answer_key.AnswerKeyStructuredProviderProtocol``
    over the OpenAI Responses adapter and the OpenRouter Chat Completions
    adapter; composed in ``di.curated_apps``.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol


class EndpointRoutedAnswerKeyProvider(AnswerKeyStructuredProviderProtocol):
    """Dispatch each request to the adapter owning the profile's endpoint."""

    def __init__(
        self,
        *,
        responses_provider: AnswerKeyStructuredProviderProtocol,
        chat_completions_provider: AnswerKeyStructuredProviderProtocol,
    ) -> None:
        self._providers: dict[StructuredLLMEndpointKind, AnswerKeyStructuredProviderProtocol] = {
            StructuredLLMEndpointKind.RESPONSES: responses_provider,
            StructuredLLMEndpointKind.CHAT_COMPLETIONS: chat_completions_provider,
        }

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        return await self._providers[profile.endpoint_kind].complete_structured(
            request=request,
            profile=profile,
        )
