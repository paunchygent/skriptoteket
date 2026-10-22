"""Inline completion trims the prefix and suffix to the configured token budget."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    LLMCompletionResponse,
)
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.editor_inline_completion_support import (
    completion_settings,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_trims_prefix_and_suffix_to_budget() -> None:
    settings = completion_settings(
        LLM_COMPLETION_ENABLED=True,
        LLM_COMPLETION_CONTEXT_WINDOW_TOKENS=50,
        LLM_COMPLETION_MAX_TOKENS=10,
        LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS=0,
        LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=5,
        LLM_COMPLETION_PREFIX_MAX_TOKENS=5,
        LLM_COMPLETION_SUFFIX_MAX_TOKENS=4,
    )
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="x", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    prefix = "A" * 25
    suffix = "B" * 25
    await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix=prefix, suffix=suffix),
    )

    assert provider.complete_inline.await_count == 1
    request = provider.complete_inline.call_args.kwargs["request"]
    assert request.prefix == "A" * 20
    assert request.suffix == "B" * 16
