from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionProviderProtocol,
    LLMCompletionResponse,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_disabled() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=False)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    handler = InlineCompletionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is False
    assert result.completion == ""
    provider.complete_inline.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_kb_unavailable() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)

    def system_prompt_loader(template_id: str) -> str:
        del template_id
        raise OSError("missing system prompt")

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=system_prompt_loader,
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is False
    assert result.completion == ""
    provider.complete_inline.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_empty_on_timeout() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    provider.complete_inline.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )

    handler = InlineCompletionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == ""
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_discards_truncated_upstream_response() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="length",
    )

    handler = InlineCompletionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == ""
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_trims_prefix_and_suffix_to_budget() -> None:
    settings = Settings(
        LLM_COMPLETION_ENABLED=True,
        LLM_COMPLETION_CONTEXT_WINDOW_TOKENS=50,
        LLM_COMPLETION_MAX_TOKENS=10,
        LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS=0,
        LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=5,
        LLM_COMPLETION_PREFIX_MAX_TOKENS=5,
        LLM_COMPLETION_SUFFIX_MAX_TOKENS=4,
    )
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="x", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=lambda _template_id: "system prompt",
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
    assert request.prefix == "A" * 10
    assert request.suffix == "B" * 8


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_empty_on_context_window_http_error() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)

    request = httpx.Request("POST", "http://test")
    response = httpx.Response(
        status_code=400,
        request=request,
        json={"error": {"message": "exceed_context_size_error"}},
    )
    provider.complete_inline.side_effect = httpx.HTTPStatusError(
        "exceed_context_size_error",
        request=request,
        response=response,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=lambda _template_id: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_unwraps_fenced_response() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n```",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "print('hello')"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_unwraps_unclosed_fence() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock(spec=InlineCompletionProviderProtocol)
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "print('hello')"
