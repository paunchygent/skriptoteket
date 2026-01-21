from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.llm.provider_sets import InlineCompletionProviders
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    LLMCompletionResponse,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.identity_fixtures import make_user


class _CharTokenCounter(TokenCounterProtocol):
    def count_text(self, text: str) -> int:
        return len(text)

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str:
        return text[: max(0, max_tokens)]

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str:
        return text[-max(0, max_tokens) :]

    def count_system_prompt(self, *, content: str) -> int:
        return len(content)

    def count_chat_message(self, *, role, content: str) -> int:
        del role
        return len(content)


class _ModelAwareTokenCounterResolver(TokenCounterResolverProtocol):
    def __init__(self) -> None:
        self._char_counter = _CharTokenCounter()

    def for_model(self, *, model: str) -> TokenCounterProtocol:
        return (
            self._char_counter
            if model == "primary-model"
            else FakeTokenCounterResolver().for_model(model=model)
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_disabled() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=False)
    provider = AsyncMock()
    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
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
async def test_inline_completion_returns_enabled_false_when_kb_unavailable() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()

    def system_prompt_loader(template_id: str, model: str) -> str:
        del template_id
        del model
        raise OSError("missing system prompt")

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
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
    provider = AsyncMock()
    provider.complete_inline.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
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
async def test_inline_completion_returns_partial_for_truncated_upstream_response() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="length",
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "partial"
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_partial_for_incomplete_upstream_response() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="incomplete",
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "partial"
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
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="x", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_empty_on_context_window_http_error() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()

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
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
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
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n```",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="```python\nprint('hello')\n",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion='"print(\\"hello\\")"',
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="def run_tooldef run_tool(input_dir: str, output_dir: str) -> dict",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="call_api (payload: dict) -> None",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="return",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="line1\nline2\nline4",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="this is a duplicated line\nkeep",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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
    settings = Settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\nkeep",
        finish_reason=None,
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=provider,
            primary_is_remote=False,
            fallback=None,
            fallback_is_remote=False,
        ),
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_uses_external_provider_by_default_when_remote_allowed() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True, AI_REMOTE_PROVIDERS_ENABLED=True)
    external = AsyncMock()
    local = AsyncMock()
    external.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\n", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=external,
            primary_is_remote=True,
            fallback=local,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix="def x():\n    ", suffix="", allow_remote_fallback=True
        ),
    )

    assert result.enabled is True
    assert result.completion == "pass"
    external.complete_inline.assert_awaited_once()
    local.complete_inline.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_uses_local_provider_when_remote_not_allowed() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True, AI_REMOTE_PROVIDERS_ENABLED=True)
    external = AsyncMock()
    local = AsyncMock()
    local.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\n", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=external,
            primary_is_remote=True,
            fallback=local,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix="def x():\n    ", suffix="", allow_remote_fallback=False
        ),
    )

    assert result.enabled is True
    assert result.completion == "pass"
    local.complete_inline.assert_awaited_once()
    external.complete_inline.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_retries_once_against_fallback_on_retryable_error() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True, AI_REMOTE_PROVIDERS_ENABLED=True)
    external = AsyncMock()
    local = AsyncMock()
    external.complete_inline.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )
    local.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\n", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=external,
            primary_is_remote=True,
            fallback=local,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix="def x():\n    ", suffix="", allow_remote_fallback=True
        ),
    )

    assert result.enabled is True
    assert result.completion == "pass"
    assert external.complete_inline.await_count == 1
    assert local.complete_inline.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_recomputes_budget_on_failover() -> None:
    settings = Settings(
        LLM_COMPLETION_ENABLED=True,
        AI_REMOTE_PROVIDERS_ENABLED=True,
        LLM_COMPLETION_MODEL="primary-model",
        LLM_COMPLETION_FALLBACK_MODEL="fallback-model",
        LLM_COMPLETION_PREFIX_MAX_TOKENS=5,
        LLM_COMPLETION_SUFFIX_MAX_TOKENS=4,
        LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=1024,
        LLM_COMPLETION_CONTEXT_WINDOW_TOKENS=4096,
        LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS=0,
        LLM_COMPLETION_MAX_TOKENS=10,
    )
    primary = AsyncMock()
    fallback = AsyncMock()
    primary.complete_inline.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )
    fallback.complete_inline.return_value = LLMCompletionResponse(
        completion="pass\n", finish_reason=None
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=primary,
            primary_is_remote=True,
            fallback=fallback,
            fallback_is_remote=False,
        ),
        capture_store=AsyncMock(),
        token_counters=_ModelAwareTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    prefix = "A" * 20
    suffix = "B" * 20
    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix=prefix,
            suffix=suffix,
            allow_remote_fallback=True,
        ),
    )

    assert result.enabled is True
    assert result.completion == "pass"

    primary_request = primary.complete_inline.call_args_list[0].kwargs["request"]
    fallback_request = fallback.complete_inline.call_args_list[0].kwargs["request"]
    assert primary_request.prefix != fallback_request.prefix
    assert len(primary_request.prefix) == 5
    assert len(fallback_request.prefix) == 20


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_notice_when_local_down_and_remote_blocked() -> None:
    settings = Settings(LLM_COMPLETION_ENABLED=True, AI_REMOTE_PROVIDERS_ENABLED=True)
    local = AsyncMock()
    external = AsyncMock()
    local.complete_inline.side_effect = httpx.ConnectError(
        "connect",
        request=httpx.Request("POST", "http://test"),
    )

    handler = InlineCompletionHandler(
        settings=settings,
        providers=InlineCompletionProviders(
            primary=local,
            primary_is_remote=False,
            fallback=external,
            fallback_is_remote=True,
        ),
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(
            prefix="def x():\n    ", suffix="", allow_remote_fallback=None
        ),
    )

    assert result.enabled is True
    assert result.completion == ""
    assert result.notice_code == "remote_fallback_required"
    assert result.notice_variant == "warning"
    assert result.notice_message
    local.complete_inline.assert_awaited_once()
    external.complete_inline.assert_not_called()
