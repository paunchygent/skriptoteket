from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from skriptoteket.application.editor.edit_suggestion_handler import EditSuggestionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import (
    EditSuggestionCommand,
    EditSuggestionProviderProtocol,
    LLMEditResponse,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_returns_enabled_false_when_disabled() -> None:
    settings = Settings(LLM_EDIT_ENABLED=False)
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)
    handler = EditSuggestionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="def x():\n    ",
            selection="return 1",
            suffix="",
            instruction="",
        ),
    )

    assert result.enabled is False
    assert result.suggestion == ""
    provider.suggest_edits.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_returns_enabled_false_when_kb_unavailable() -> None:
    settings = Settings(LLM_EDIT_ENABLED=True)
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)

    def system_prompt_loader(template_id: str) -> str:
        del template_id
        raise OSError("missing system prompt")

    handler = EditSuggestionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=system_prompt_loader,
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="def x():\n    ",
            selection="return 1",
            suffix="",
            instruction="",
        ),
    )

    assert result.enabled is False
    assert result.suggestion == ""
    provider.suggest_edits.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_returns_empty_on_timeout() -> None:
    settings = Settings(LLM_EDIT_ENABLED=True)
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)
    provider.suggest_edits.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )

    handler = EditSuggestionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="def x():\n    ",
            selection="return 1",
            suffix="",
            instruction="",
        ),
    )

    assert result.enabled is True
    assert result.suggestion == ""
    provider.suggest_edits.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_discards_truncated_upstream_response() -> None:
    settings = Settings(LLM_EDIT_ENABLED=True)
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)
    provider.suggest_edits.return_value = LLMEditResponse(
        suggestion="partial",
        finish_reason="length",
    )

    handler = EditSuggestionHandler(settings=settings, provider=provider)
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="def x():\n    ",
            selection="return 1",
            suffix="",
            instruction="",
        ),
    )

    assert result.enabled is True
    assert result.suggestion == ""
    provider.suggest_edits.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_preserves_selection_and_trims_prefix_suffix_first() -> None:
    settings = Settings(
        LLM_EDIT_ENABLED=True,
        LLM_EDIT_CONTEXT_WINDOW_TOKENS=100,
        LLM_EDIT_MAX_TOKENS=10,
        LLM_EDIT_CONTEXT_SAFETY_MARGIN_TOKENS=0,
        LLM_EDIT_SYSTEM_PROMPT_MAX_TOKENS=10,
        LLM_EDIT_INSTRUCTION_MAX_TOKENS=2,
        LLM_EDIT_SELECTION_MAX_TOKENS=5,
        LLM_EDIT_PREFIX_MAX_TOKENS=8,
        LLM_EDIT_SUFFIX_MAX_TOKENS=2,
    )
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)
    provider.suggest_edits.return_value = LLMEditResponse(suggestion="ok", finish_reason=None)

    handler = EditSuggestionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=lambda _template_id: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    selection = "S" * 30
    await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="P" * 40,
            selection=selection,
            suffix="U" * 40,
            instruction="Gör bättre.",
        ),
    )

    assert provider.suggest_edits.await_count == 1
    request = provider.suggest_edits.call_args.kwargs["request"]
    assert request.selection == selection
    assert request.prefix == ""
    assert request.suffix == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_suggestion_returns_empty_on_context_window_http_error() -> None:
    settings = Settings(LLM_EDIT_ENABLED=True)
    provider = AsyncMock(spec=EditSuggestionProviderProtocol)

    request = httpx.Request("POST", "http://test")
    response = httpx.Response(
        status_code=400,
        request=request,
        json={"error": {"message": "exceed_context_size_error"}},
    )
    provider.suggest_edits.side_effect = httpx.HTTPStatusError(
        "exceed_context_size_error",
        request=request,
        response=response,
    )

    handler = EditSuggestionHandler(
        settings=settings,
        provider=provider,
        system_prompt_loader=lambda _template_id: "system prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    result = await handler.handle(
        actor=actor,
        command=EditSuggestionCommand(
            prefix="def x():\n    ",
            selection="return 1",
            suffix="",
            instruction="",
        ),
    )

    assert result.enabled is True
    assert result.suggestion == ""
