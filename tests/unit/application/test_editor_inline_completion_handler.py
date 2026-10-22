from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    ai_try_again_note,
)
from skriptoteket.protocols.llm import (
    EditorLlmProviderError,
    InlineCompletionCommand,
    LLMCompletionResponse,
)
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.identity_fixtures import make_user


def _settings(**overrides: Any) -> Settings:
    return Settings(
        HULEEDU_LLM_PROVIDER_BASE_URL="http://door.test",
        HULEEDU_INTERNAL_API_KEY="test-internal-key",
        **overrides,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_disabled() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=False)
    provider = AsyncMock()
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

    assert result.enabled is False
    assert result.completion == ""
    provider.complete_inline.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_kb_unavailable() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()

    def system_prompt_loader(template_id: str, model: str) -> str:
        del template_id
        del model
        raise OSError("missing system prompt")

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.side_effect = EditorLlmProviderError(kind="timeout")

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
    assert result.completion == ""
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_partial_for_truncated_upstream_response() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="length",
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
    assert result.completion == "partial"
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_partial_for_incomplete_upstream_response() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="incomplete",
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
    assert result.completion == "partial"
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_trims_prefix_and_suffix_to_budget() -> None:
    settings = _settings(
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_empty_on_context_window_exceeded() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()

    provider.complete_inline.side_effect = EditorLlmProviderError(
        kind="context_window_exceeded", status_code=400
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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
    settings = _settings(LLM_COMPLETION_ENABLED=True)
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_handle_leaves_role_admission_to_the_web_gate() -> None:
    settings = _settings(LLM_COMPLETION_ENABLED=True)
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(
        completion="partial",
        finish_reason="length",
    )

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.USER)

    result = await handler.handle(
        actor=actor,
        command=InlineCompletionCommand(prefix="def x():\n    ", suffix=""),
    )

    assert result.enabled is True
    assert result.completion == "partial"
    provider.complete_inline.assert_awaited_once()


def _handler(provider: AsyncMock) -> InlineCompletionHandler:
    return InlineCompletionHandler(
        settings=_settings(LLM_COMPLETION_ENABLED=True),
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id, _model: "system prompt",
    )


_COMMAND = InlineCompletionCommand(prefix="def x():\n    ", suffix="")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(("role", "exempt"), [(Role.ADMIN, True), (Role.CONTRIBUTOR, False)])
async def test_inline_completion_calls_provider_with_the_actors_door_caller(
    role: Role, exempt: bool
) -> None:
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(completion="x")
    actor = make_user(role=role)

    await _handler(provider).handle(actor=actor, command=_COMMAND)

    provider.complete_inline.assert_awaited_once()
    caller = provider.complete_inline.call_args.kwargs["caller"]
    assert caller.user_id == actor.id
    assert caller.exempt is exempt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_uses_the_single_configured_template() -> None:
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(completion="x")
    seen: list[tuple[str, str]] = []

    def loader(template_id: str, model: str) -> str:
        seen.append((template_id, model))
        return "system prompt"

    settings = _settings(LLM_COMPLETION_ENABLED=True)
    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=loader,
    )

    result = await handler.handle(actor=make_user(role=Role.CONTRIBUTOR), command=_COMMAND)

    assert seen == [("inline_completion_gpt5_v1", settings.LLM_COMPLETION_MODEL)]
    assert result.eval_meta is not None
    assert result.eval_meta.template_id == "inline_completion_gpt5_v1"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "message"),
    [
        (
            AiDailyLimit.USER_SHARE,
            "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.",
        ),
        (AiDailyLimit.POOL, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
    ],
)
async def test_inline_completion_limit_refusal_raises_the_429_domain_error(
    limit: AiDailyLimit, message: str
) -> None:
    provider = AsyncMock()
    provider.complete_inline.side_effect = AiDailyLimitReached(limit=limit)

    with pytest.raises(DomainError) as raised:
        await _handler(provider).handle(actor=make_user(role=Role.CONTRIBUTOR), command=_COMMAND)

    assert raised.value.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert raised.value.message == message
    assert raised.value.details == {"limit": limit.value}
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_busy_door_raises_the_try_again_error() -> None:
    provider = AsyncMock()
    provider.complete_inline.side_effect = AiDoorBusy(retry_after_seconds=None)

    with pytest.raises(DomainError) as raised:
        await _handler(provider).handle(actor=make_user(role=Role.CONTRIBUTOR), command=_COMMAND)

    assert raised.value.code is ErrorCode.AI_TRY_AGAIN
    assert raised.value.message == ai_try_again_note()
    assert raised.value.details == {}
    provider.complete_inline.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "outcome"),
    [
        (EditorLlmProviderError(kind="timeout"), "timeout"),
        (EditorLlmProviderError(kind="http_status", status_code=503), "error"),
        (EditorLlmProviderError(kind="request_failed"), "error"),
        (EditorLlmProviderError(kind="invalid_response"), "error"),
        (EditorLlmProviderError(kind="context_window_exceeded"), "over_budget"),
    ],
)
async def test_inline_completion_provider_failure_is_an_empty_enabled_result(
    error: EditorLlmProviderError, outcome: str
) -> None:
    provider = AsyncMock()
    provider.complete_inline.side_effect = error

    result = await _handler(provider).handle(
        actor=make_user(role=Role.CONTRIBUTOR), command=_COMMAND
    )

    assert result.enabled is True
    assert result.completion == ""
    assert result.eval_meta is not None
    assert result.eval_meta.outcome == outcome
    provider.complete_inline.assert_awaited_once()
