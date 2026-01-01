"""LLM provider: editor inline completions (ghost text)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.application.editor.edit_suggestion_handler import EditSuggestionHandler
from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai_provider import (
    OpenAIEditSuggestionProvider,
    OpenAIInlineCompletionProvider,
)
from skriptoteket.protocols.llm import (
    EditSuggestionHandlerProtocol,
    EditSuggestionProviderProtocol,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderProtocol,
)


class LlmProvider(Provider):
    @provide(scope=Scope.APP)
    async def llm_http_client(self, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
        timeout = httpx.Timeout(settings.LLM_COMPLETION_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            yield client

    @provide(scope=Scope.APP)
    def inline_completion_provider(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> InlineCompletionProviderProtocol:
        return OpenAIInlineCompletionProvider(settings=settings, client=client)

    @provide(scope=Scope.APP)
    def edit_suggestion_provider(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> EditSuggestionProviderProtocol:
        return OpenAIEditSuggestionProvider(settings=settings, client=client)

    @provide(scope=Scope.REQUEST)
    def inline_completion_handler(
        self,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
    ) -> InlineCompletionHandlerProtocol:
        return InlineCompletionHandler(settings=settings, provider=provider)

    @provide(scope=Scope.REQUEST)
    def edit_suggestion_handler(
        self,
        settings: Settings,
        provider: EditSuggestionProviderProtocol,
    ) -> EditSuggestionHandlerProtocol:
        return EditSuggestionHandler(settings=settings, provider=provider)
