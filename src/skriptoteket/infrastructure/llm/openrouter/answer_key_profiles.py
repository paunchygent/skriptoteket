"""GLM-5.3-flash OpenRouter answer-key failover profile.

Purpose:
    Pin the GLM-5.3-flash chat-completions profile as the failover-only
    backup for the answer-key lane, ported from sir-convert-a-lot
    `76983339` (D12-D13).

Relationships:
    Model identifier `z-ai/glm-5.3-flash` verified against the current
    OpenRouter model catalog (GET https://openrouter.ai/api/v1/models,
    canonical slug `z-ai/glm-5.3-flash-20260826`) at implementation time;
    the model supports `response_format`/`structured_outputs`.
"""

from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)

OPENROUTER_GLM53_FLASH_PROVIDER_ID = "openrouter-glm-5.3-flash"
OPENROUTER_GLM53_FLASH_MODEL = "z-ai/glm-5.3-flash"


def build_glm_failover_answer_key_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """Build the pinned GLM failover profile from operator-configurable settings."""

    return StructuredLLMProviderProfile(
        provider_id=OPENROUTER_GLM53_FLASH_PROVIDER_ID,
        model=settings.LLM_ANSWER_KEY_FAILOVER_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        is_remote=True,
        context_window_tokens=settings.LLM_ANSWER_KEY_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=settings.LLM_ANSWER_KEY_MAX_OUTPUT_TOKENS,
        temperature=settings.LLM_ANSWER_KEY_TEMPERATURE,
    )
