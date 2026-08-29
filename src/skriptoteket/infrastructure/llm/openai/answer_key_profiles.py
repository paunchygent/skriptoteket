"""GPT-5.6 Luna answer-key provider profile and Luna-only selection.

Purpose:
    Pin the GPT-5.6 Luna low-reasoning-effort profile as the only provider
    path for TASK-SKRIPT-39-02-01 and implement the provider-selection seam
    that TASK-SKRIPT-39-02-02 extends with GLM failover.

Relationships:
    Model identifier `gpt-5.6-luna` verified against current OpenAI docs
    (developers.openai.com/api/docs/models/gpt-5.6-luna) at implementation
    time; profile defaults carry over from sir-convert-a-lot `76983339`.
"""

from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMTextVerbosity,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyProviderSelectorProtocol

OPENAI_GPT56_LUNA_PROVIDER_ID = "openai-gpt-5.6-luna"
OPENAI_GPT56_LUNA_MODEL = "gpt-5.6-luna"


def build_luna_answer_key_profile(settings: Settings) -> StructuredLLMProviderProfile:
    """Build the pinned Luna profile from operator-configurable settings."""

    return StructuredLLMProviderProfile(
        provider_id=OPENAI_GPT56_LUNA_PROVIDER_ID,
        model=settings.LLM_ANSWER_KEY_MODEL,
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=settings.LLM_ANSWER_KEY_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=settings.LLM_ANSWER_KEY_MAX_OUTPUT_TOKENS,
        temperature=settings.LLM_ANSWER_KEY_TEMPERATURE,
        reasoning_effort=StructuredLLMReasoningEffort(settings.LLM_ANSWER_KEY_REASONING_EFFORT),
        text_verbosity=StructuredLLMTextVerbosity(settings.LLM_ANSWER_KEY_TEXT_VERBOSITY),
    )


class LunaOnlyAnswerKeyProviderSelector(AnswerKeyProviderSelectorProtocol):
    """Provider selection with exactly one path: the Luna profile."""

    def __init__(self, *, profile: StructuredLLMProviderProfile) -> None:
        self._profile = profile

    def select_profile(self) -> StructuredLLMProviderProfile:
        return self._profile
