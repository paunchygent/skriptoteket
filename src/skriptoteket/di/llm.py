"""LLM providers and handlers for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.clear_chat_handler import EditorChatClearHandler
from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.application.editor.edit_suggestion_handler import EditSuggestionHandler
from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.chat_inflight_guard import InProcessChatInFlightGuard
from skriptoteket.infrastructure.llm.openai_provider import (
    OpenAIChatStreamProvider,
    OpenAIEditSuggestionProvider,
    OpenAIInlineCompletionProvider,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatInFlightGuardProtocol,
    ChatStreamProviderProtocol,
    EditorChatClearHandlerProtocol,
    EditorChatHandlerProtocol,
    EditSuggestionHandlerProtocol,
    EditSuggestionProviderProtocol,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderProtocol,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


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

    @provide(scope=Scope.APP)
    def chat_stream_provider(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> ChatStreamProviderProtocol:
        return OpenAIChatStreamProvider(settings=settings, client=client)

    @provide(scope=Scope.APP)
    def chat_inflight_guard(self) -> ChatInFlightGuardProtocol:
        return InProcessChatInFlightGuard()

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

    @provide(scope=Scope.REQUEST)
    def editor_chat_handler(
        self,
        settings: Settings,
        provider: ChatStreamProviderProtocol,
        guard: ChatInFlightGuardProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> EditorChatHandlerProtocol:
        return EditorChatHandler(
            settings=settings,
            provider=provider,
            guard=guard,
            uow=uow,
            sessions=sessions,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def editor_chat_clear_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> EditorChatClearHandlerProtocol:
        return EditorChatClearHandler(uow=uow, sessions=sessions, messages=messages)
