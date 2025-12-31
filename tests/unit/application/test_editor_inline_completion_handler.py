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

    def kb_loader() -> str:
        raise OSError("missing kb")

    handler = InlineCompletionHandler(
        settings=settings,
        provider=provider,
        kb_loader=kb_loader,
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
