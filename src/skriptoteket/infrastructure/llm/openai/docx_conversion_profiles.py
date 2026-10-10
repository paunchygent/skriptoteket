"""GPT-6 Luna DOCX exam-conversion provider profile.

Purpose:
    Pin the GPT-6 Luna medium-reasoning-effort profile as the primary
    Responses profile for DOCX exam conversion; answer-key enrichment keeps
    ``infrastructure.llm.openai.answer_key_profiles``.

Relationships:
    Model identifier `gpt-6-luna`, its 1,050,000-token context window,
    128,000 max output tokens, Responses structured-output support and
    reasoning efforts (`none`, `low`, `medium`, `high`, `xhigh`, `max`)
    verified against current OpenAI docs
    (developers.openai.com/api/docs/models/compare and
    developers.openai.com/api/docs/guides/deployment-checklist) on 2026-10-10.
"""

from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)

OPENAI_GPT6_LUNA_PROVIDER_ID = "openai-gpt-6-luna"


def build_luna_docx_conversion_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """Build the pinned DOCX-conversion Luna profile from operator-configurable settings."""

    return StructuredLLMProviderProfile(
        provider_id=OPENAI_GPT6_LUNA_PROVIDER_ID,
        model=settings.LLM_DOCX_CONVERSION_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=settings.LLM_DOCX_CONVERSION_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=settings.LLM_DOCX_CONVERSION_MAX_OUTPUT_TOKENS,
        temperature=settings.LLM_ANSWER_KEY_TEMPERATURE,
        reasoning_effort=StructuredLLMReasoningEffort(
            settings.LLM_DOCX_CONVERSION_REASONING_EFFORT
        ),
        text_verbosity=StructuredLLMTextVerbosity(settings.LLM_ANSWER_KEY_TEXT_VERBOSITY),
    )
