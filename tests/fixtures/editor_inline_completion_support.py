"""Settings and handler wiring shared by the inline completion handler tests."""

from __future__ import annotations

from typing import TypedDict, Unpack
from unittest.mock import AsyncMock

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.config import Settings
from skriptoteket.protocols.llm import InlineCompletionCommand
from tests.fixtures.application_fixtures import FakeTokenCounterResolver


class CompletionSettingsOverrides(TypedDict, total=False):
    """The completion settings the handler tests vary, each with its real type."""

    LLM_COMPLETION_ENABLED: bool
    LLM_COMPLETION_CONTEXT_WINDOW_TOKENS: int
    LLM_COMPLETION_MAX_TOKENS: int
    LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS: int
    LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS: int
    LLM_COMPLETION_PREFIX_MAX_TOKENS: int
    LLM_COMPLETION_SUFFIX_MAX_TOKENS: int


COMPLETION_COMMAND = InlineCompletionCommand(prefix="def x():\n    ", suffix="")


def completion_settings(**overrides: Unpack[CompletionSettingsOverrides]) -> Settings:
    return Settings(
        HULEEDU_LLM_PROVIDER_BASE_URL="http://door.test",
        HULEEDU_INTERNAL_API_KEY="test-internal-key",
        **overrides,
    )


def completion_handler(provider: AsyncMock) -> InlineCompletionHandler:
    return InlineCompletionHandler(
        settings=completion_settings(LLM_COMPLETION_ENABLED=True),
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
