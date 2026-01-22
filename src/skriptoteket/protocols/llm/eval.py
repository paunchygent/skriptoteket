"""Evaluation metadata for LLM prompt handling."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]


class PromptEvalMeta(BaseModel):
    """Evaluation-only metadata (never includes prompts/code/model output text)."""

    model_config = ConfigDict(frozen=True)

    template_id: str | None
    outcome: PromptEvalOutcome
    system_prompt_chars: int
    system_prompt_tokens: int | None = None
    prefix_chars: int = 0
    suffix_chars: int = 0
    prefix_tokens: int | None = None
    suffix_tokens: int | None = None
    prompt_tokens_total: int | None = None
    prompt_budget_tokens: int | None = None
    instruction_chars: int = 0
    selection_chars: int = 0
    raw_chars: int | None = None
    normalized_chars: int | None = None
    prefix_overlap_chars: int | None = None
    suffix_overlap_chars: int | None = None
    prepare_ms: int | None = None
    provider_ms: int | None = None
    normalize_ms: int | None = None
    total_ms: int | None = None
