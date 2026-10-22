"""Inline completion admission, door refusals and provider failures."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
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
from tests.fixtures.editor_inline_completion_support import (
    COMPLETION_COMMAND,
    completion_handler,
    completion_settings,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_returns_enabled_false_when_disabled() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=False)
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
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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
async def test_inline_completion_returns_empty_on_context_window_exceeded() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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
async def test_inline_completion_handle_leaves_role_admission_to_the_web_gate() -> None:
    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
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


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(("role", "exempt"), [(Role.ADMIN, True), (Role.CONTRIBUTOR, False)])
async def test_inline_completion_calls_provider_with_the_actors_door_caller(
    role: Role, exempt: bool
) -> None:
    provider = AsyncMock()
    provider.complete_inline.return_value = LLMCompletionResponse(completion="x")
    actor = make_user(role=role)

    await completion_handler(provider).handle(actor=actor, command=COMPLETION_COMMAND)

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

    settings = completion_settings(LLM_COMPLETION_ENABLED=True)
    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        capture_store=AsyncMock(),
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=loader,
    )

    result = await handler.handle(
        actor=make_user(role=Role.CONTRIBUTOR), command=COMPLETION_COMMAND
    )

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
        await completion_handler(provider).handle(
            actor=make_user(role=Role.CONTRIBUTOR), command=COMPLETION_COMMAND
        )

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
        await completion_handler(provider).handle(
            actor=make_user(role=Role.CONTRIBUTOR), command=COMPLETION_COMMAND
        )

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

    result = await completion_handler(provider).handle(
        actor=make_user(role=Role.CONTRIBUTOR), command=COMPLETION_COMMAND
    )

    assert result.enabled is True
    assert result.completion == ""
    assert result.eval_meta is not None
    assert result.eval_meta.outcome == outcome
    provider.complete_inline.assert_awaited_once()
