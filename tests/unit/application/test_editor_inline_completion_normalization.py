"""Inline completion normalizes the model output before it reaches the editor."""

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
async def test_inline_completion_unwraps_fenced_response() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n```",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
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
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "print('hello')"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_unwraps_quoted_response() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion='"print(\\"hello\\")"',
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == 'print("hello")'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_strips_cursor_boundary_overlap() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="def run_tooldef run_tool(input_dir: str, output_dir: str) -> dict",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def run_tool", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "(input_dir: str, output_dir: str) -> dict"
    assert result.eval_meta is not None
    assert result.eval_meta.prefix_overlap_chars == 24


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_strips_token_overlap_with_whitespace() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="call_api (payload: dict) -> None",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="call_api(", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "payload: dict) -> None"
    assert result.eval_meta is not None
    assert result.eval_meta.prefix_overlap_chars == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_sets_replace_suffix_chars_for_partial_token() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="return",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="retu", suffix="rn"),
    )

    assert result.enabled is True
    assert result.completion == "rn"
    assert result.replace_suffix_chars == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_drops_two_line_echo() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="line1\nline2\nline4",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="line1\nline2\nline3\n", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_strips_duplicate_lines_over_threshold() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="this is a duplicated line\nkeep",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix="this is a duplicated line\ncontext\n",
            suffix="",
        ),
    )

    assert result.enabled is True
    assert result.completion == "keep"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_keeps_short_duplicate_lines() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\nkeep",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="pass\ncontext\n", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "pass\nkeep"
