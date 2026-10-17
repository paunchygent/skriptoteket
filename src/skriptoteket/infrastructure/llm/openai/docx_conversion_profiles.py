"""GPT-6 Luna DOCX exam-conversion provider profiles.

Purpose:
    Pin the GPT-6 Luna medium-reasoning-effort profile as the primary
    Responses profile for DOCX exam conversion, the low-effort grouping pass and
    the label-only second pass (TASK-SKRIPT-39-05-04 D23: medium effort, low
    verbosity); answer-key enrichment keeps
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
OPENAI_GPT6_LUNA_GROUPING_PROVIDER_ID = "openai-gpt-6-luna-grouping"
OPENAI_GPT6_LUNA_ITEM_LABEL_PROVIDER_ID = "openai-gpt-6-luna-item-label"
LUNA_MAX_OUTPUT_TOKENS = 128_000


def build_luna_docx_conversion_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """Build the pinned DOCX-conversion Luna profile from operator-configurable settings.

    One converter batch reserves and may spend the output allowance of its families, never
    a whole exam's, so a many-family exam fits the daily token lease at once.
    """

    return StructuredLLMProviderProfile(
        provider_id=OPENAI_GPT6_LUNA_PROVIDER_ID,
        model=settings.LLM_DOCX_CONVERSION_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=settings.LLM_DOCX_CONVERSION_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=min(
            settings.LLM_DOCX_BATCH_OUTPUT_TOKENS_PER_FAMILY * settings.LLM_DOCX_BATCH_FAMILIES,
            LUNA_MAX_OUTPUT_TOKENS,
        ),
        reasoning_effort=StructuredLLMReasoningEffort(
            settings.LLM_DOCX_CONVERSION_REASONING_EFFORT
        ),
        text_verbosity=StructuredLLMTextVerbosity(settings.LLM_ANSWER_KEY_TEXT_VERBOSITY),
    )


def build_luna_docx_grouping_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """The grouping pass returns source references only, at low effort."""

    return StructuredLLMProviderProfile(
        provider_id=OPENAI_GPT6_LUNA_GROUPING_PROVIDER_ID,
        model=settings.LLM_DOCX_CONVERSION_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=settings.LLM_DOCX_CONVERSION_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=settings.LLM_DOCX_GROUPING_MAX_OUTPUT_TOKENS,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
        text_verbosity=StructuredLLMTextVerbosity(settings.LLM_ANSWER_KEY_TEXT_VERBOSITY),
    )


def build_luna_item_label_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """The second labeling pass decides one question's label alone (D23)."""

    return StructuredLLMProviderProfile(
        provider_id=OPENAI_GPT6_LUNA_ITEM_LABEL_PROVIDER_ID,
        model=settings.LLM_DOCX_CONVERSION_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=settings.LLM_DOCX_CONVERSION_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=settings.LLM_ITEM_LABELER_SECOND_PASS_MAX_OUTPUT_TOKENS,
        reasoning_effort=StructuredLLMReasoningEffort.MEDIUM,
        text_verbosity=StructuredLLMTextVerbosity.LOW,
    )
